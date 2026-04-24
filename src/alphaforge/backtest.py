from __future__ import annotations

"""Canonical execution semantics and runtime artifact contracts.

This module owns the MVP long-flat execution law for AlphaForge. Strategies
emit next-bar target positions, while this module decides how those targets
become realized positions, turnover, costs, equity, and trade records.
"""

from collections.abc import Sequence

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
    target_positions: pd.Series | Sequence[float],
    config: BacktestConfig,
) -> tuple[EquityCurveFrame, pd.DataFrame]:
    """Run the canonical MVP long-flat backtest on validated market data.

    Strategy outputs are interpreted as target positions for the next tradable
    interval. This execution layer applies a one-bar lag, computes
    close-to-close returns, charges turnover-based fee and slippage costs, and
    compounds equity multiplicatively from the configured initial capital.
    """
    frame = market_data.copy()
    coerced_target_positions = _coerce_target_positions(target_positions, frame.index)
    frame["target_position"] = coerced_target_positions.astype(float).fillna(0.0).clip(lower=0.0, upper=1.0)
    frame["position"] = frame["target_position"].shift(1).fillna(0.0)
    frame["close_return"] = frame["close"].pct_change().fillna(0.0)
    frame["turnover"] = frame["position"].diff().abs().fillna(frame["position"].abs())
    trading_cost = frame["turnover"] * (config.fee_rate + config.slippage_rate)
    frame["strategy_return"] = (frame["position"] * frame["close_return"]) - trading_cost
    frame["equity"] = config.initial_capital * (1.0 + frame["strategy_return"]).cumprod()

    trades = _extract_trades(frame)
    trade_frame = pd.DataFrame([trade.__dict__ for trade in trades], columns=list(BACKTEST_TRADE_LOG_COLUMNS))
    return frame.reindex(columns=BACKTEST_EQUITY_CURVE_COLUMNS), trade_frame


def _coerce_target_positions(target_positions: pd.Series | Sequence[float], data_index: pd.Index) -> pd.Series:
    """Validate target-position row mapping before execution normalization."""
    expected_length = len(data_index)
    if isinstance(target_positions, pd.Series):
        if len(target_positions) != expected_length:
            raise ValueError("target_positions length must match market data row count")
        if not target_positions.index.equals(data_index):
            raise ValueError("target_positions index alignment must exactly match market data index")
        return pd.Series(target_positions.to_numpy(), index=data_index, name="target_position")

    try:
        actual_length = len(target_positions)
    except TypeError as exc:
        raise ValueError("target_positions length must match market data row count") from exc
    if actual_length != expected_length:
        raise ValueError("target_positions length must match market data row count")
    return pd.Series(target_positions, index=data_index, name="target_position")


def _extract_trades(frame: pd.DataFrame) -> list[TradeRecord]:
    """Extract runtime trade records from realized positions.

    A trade starts when realized position changes from flat to long, and ends
    when realized position changes from long to flat. Any open position is
    closed on the final sample bar so the runtime trade log has explicit exits.
    """
    if frame.empty:
        return []

    position = frame["position"].astype(float)
    previous_position = position.shift(1, fill_value=0.0)
    entry_mask = previous_position.eq(0.0) & position.gt(0.0)
    exit_mask = previous_position.gt(0.0) & position.eq(0.0)

    if not bool(entry_mask.any()):
        return []

    trade_ids = entry_mask.cumsum().astype(int)
    active_trade_ids = trade_ids.where(position.gt(0.0) | exit_mask, 0)

    entry_rows = frame.loc[entry_mask, ["datetime", "close"]].copy()
    entry_rows["trade_id"] = trade_ids.loc[entry_mask].to_numpy()
    entry_rows.rename(columns={"datetime": "entry_time", "close": "entry_price"}, inplace=True)

    exit_rows = frame.loc[exit_mask, ["datetime", "close"]].copy()
    exit_rows["trade_id"] = trade_ids.loc[exit_mask].to_numpy()
    exit_rows["quantity"] = previous_position.loc[exit_mask].astype(float).to_numpy()
    exit_rows.rename(columns={"datetime": "exit_time", "close": "exit_price"}, inplace=True)

    final_trade_id = int(trade_ids.max())
    if float(position.iloc[-1]) > 0.0 and final_trade_id not in set(exit_rows["trade_id"].tolist()):
        exit_rows = pd.concat(
            [
                exit_rows,
                pd.DataFrame(
                    {
                        "exit_time": [frame.iloc[-1]["datetime"]],
                        "exit_price": [frame.iloc[-1]["close"]],
                        "trade_id": [final_trade_id],
                        "quantity": [float(position.iloc[-1])],
                    }
                ),
            ],
            ignore_index=True,
        )

    net_pnl_by_trade = (
        frame.assign(trade_id=active_trade_ids)
        .loc[lambda df: df["trade_id"] > 0]
        .groupby("trade_id", sort=True)["strategy_return"]
        .sum()
    )

    trade_frame = (
        entry_rows.merge(exit_rows, on="trade_id", how="inner")
        .sort_values("trade_id")
        .assign(
            side="long",
            net_pnl=lambda df: df["trade_id"].map(net_pnl_by_trade).astype(float),
        )
    )
    trade_frame["entry_time"] = trade_frame["entry_time"].map(str)
    trade_frame["exit_time"] = trade_frame["exit_time"].map(str)
    trade_frame["entry_price"] = trade_frame["entry_price"].astype(float)
    trade_frame["exit_price"] = trade_frame["exit_price"].astype(float)
    trade_frame["gross_return"] = (
        trade_frame["exit_price"]
        .div(trade_frame["entry_price"].replace(0.0, float("nan")))
        .sub(1.0)
        .fillna(0.0)
        .astype(float)
    )

    return [
        TradeRecord(
            entry_time=row.entry_time,
            exit_time=row.exit_time,
            side=row.side,
            quantity=float(row.quantity),
            entry_price=float(row.entry_price),
            exit_price=float(row.exit_price),
            gross_return=float(row.gross_return),
            net_pnl=float(row.net_pnl),
        )
        for row in trade_frame.itertuples(index=False)
    ]
