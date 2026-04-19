from __future__ import annotations

"""Canonical execution semantics and runtime artifact contracts.

This module owns the MVP long-flat execution law for AlphaForge. Strategies
emit next-bar target positions, while this module decides how those targets
become realized positions, turnover, costs, equity, and trade records.
"""

import pandas as pd

from .schemas import EquityCurveFrame, BacktestConfig, TradeRecord

BACKTEST_EQUITY_CURVE_COLUMNS = (
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "target_position",
    "position",
    "close_return",
    "turnover",
    "strategy_return",
    "equity",
)

BACKTEST_TRADE_LOG_COLUMNS = tuple(TradeRecord.__annotations__.keys())


def run_backtest(
    market_data: pd.DataFrame,
    target_positions: pd.Series,
    config: BacktestConfig,
) -> tuple[EquityCurveFrame, pd.DataFrame]:
    """Run the canonical MVP long-flat backtest on validated market data.

    Strategy outputs are interpreted as target positions for the next tradable
    interval. This execution layer applies a one-bar lag, computes
    close-to-close returns, charges turnover-based fee and slippage costs, and
    compounds equity multiplicatively from the configured initial capital.
    """
    frame = market_data.copy()
    frame["target_position"] = target_positions.astype(float).fillna(0.0).clip(lower=0.0, upper=1.0)
    frame["position"] = frame["target_position"].shift(1).fillna(0.0)
    frame["close_return"] = frame["close"].pct_change().fillna(0.0)
    frame["turnover"] = frame["position"].diff().abs().fillna(frame["position"].abs())
    trading_cost = frame["turnover"] * (config.fee_rate + config.slippage_rate)
    frame["strategy_return"] = (frame["position"] * frame["close_return"]) - trading_cost
    frame["equity"] = config.initial_capital * (1.0 + frame["strategy_return"]).cumprod()

    trades = _extract_trades(frame)
    trade_frame = pd.DataFrame([trade.__dict__ for trade in trades], columns=list(BACKTEST_TRADE_LOG_COLUMNS))
    return frame.reindex(columns=BACKTEST_EQUITY_CURVE_COLUMNS), trade_frame


def _extract_trades(frame: pd.DataFrame) -> list[TradeRecord]:
    """Extract runtime trade records from realized positions.

    A trade starts when realized position changes from flat to long, and ends
    when realized position changes from long to flat. Any open position is
    closed on the final sample bar so the runtime trade log has explicit exits.
    """
    trades: list[TradeRecord] = []
    in_trade = False
    entry_index = -1
    entry_price = 0.0

    for idx in range(len(frame)):
        current_position = float(frame.iloc[idx]["position"])
        previous_position = float(frame.iloc[idx - 1]["position"]) if idx > 0 else 0.0

        if not in_trade and previous_position == 0.0 and current_position > 0.0:
            in_trade = True
            entry_index = idx
            entry_price = float(frame.iloc[idx]["close"])
            continue

        if in_trade and previous_position > 0.0 and current_position == 0.0:
            exit_index = idx
            exit_price = float(frame.iloc[idx]["close"])
            quantity = previous_position
            gross_return = (exit_price / entry_price) - 1.0 if entry_price else 0.0
            net_pnl = float(frame.iloc[entry_index: exit_index + 1]["strategy_return"].sum())
            trades.append(
                TradeRecord(
                    entry_time=str(frame.iloc[entry_index]["datetime"]),
                    exit_time=str(frame.iloc[exit_index]["datetime"]),
                    side="long",
                    quantity=quantity,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    gross_return=gross_return,
                    net_pnl=net_pnl,
                )
            )
            in_trade = False

    if in_trade:
        exit_index = len(frame) - 1
        exit_price = float(frame.iloc[exit_index]["close"])
        quantity = float(frame.iloc[exit_index]["position"])
        gross_return = (exit_price / entry_price) - 1.0 if entry_price else 0.0
        net_pnl = float(frame.iloc[entry_index: exit_index + 1]["strategy_return"].sum())
        trades.append(
            TradeRecord(
                entry_time=str(frame.iloc[entry_index]["datetime"]),
                exit_time=str(frame.iloc[exit_index]["datetime"]),
                side="long",
                quantity=quantity,
                entry_price=entry_price,
                exit_price=exit_price,
                gross_return=gross_return,
                net_pnl=net_pnl,
            )
        )

    return trades
