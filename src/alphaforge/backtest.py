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
EXECUTION_SEMANTICS = "legacy_close_to_close_lagged"


def build_execution_semantics_metadata() -> dict[str, object]:
    """Describe the canonical execution law used by the current backtest."""
    return {
        "execution_semantics": EXECUTION_SEMANTICS,
        "position_rule": "position[t] = target_position[t-1]",
        "return_rule": "close_to_close",
        "position_bounds": [0.0, 1.0],
        "supports_shorting": False,
        "supports_leverage": False,
    }


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

    entry_rows = frame.loc[entry_mask, ["datetime", "close", "target_position"]].copy()
    entry_rows["trade_id"] = trade_ids.loc[entry_mask].to_numpy()
    entry_rows["entry_target_position"] = frame["target_position"].shift(1).loc[entry_mask].fillna(0.0).astype(float).to_numpy()
    entry_rows.rename(columns={"datetime": "entry_datetime", "close": "entry_price"}, inplace=True)
    entry_rows.drop(columns=["target_position"], inplace=True)

    exit_rows = frame.loc[exit_mask, ["datetime", "close", "target_position"]].copy()
    exit_rows["trade_id"] = trade_ids.loc[exit_mask].to_numpy()
    exit_rows.rename(columns={"datetime": "exit_datetime", "close": "exit_price", "target_position": "exit_target_position"}, inplace=True)

    final_trade_id = int(trade_ids.max())
    if float(position.iloc[-1]) > 0.0 and final_trade_id not in set(exit_rows["trade_id"].tolist()):
        exit_rows = pd.concat(
            [
                exit_rows,
                pd.DataFrame(
                    {
                        "exit_datetime": [frame.iloc[-1]["datetime"]],
                        "exit_price": [frame.iloc[-1]["close"]],
                        "trade_id": [final_trade_id],
                        "exit_target_position": [float(frame.iloc[-1]["target_position"])],
                    }
                ),
            ],
            ignore_index=True,
        )

    gross_return_by_trade = (
        frame.assign(trade_id=active_trade_ids)
        .loc[lambda df: df["trade_id"] > 0]
        .loc[lambda df: df["position"].astype(float) > 0.0]
        .groupby("trade_id", sort=True)["close_return"]
        .apply(lambda series: float((1.0 + series.astype(float)).prod() - 1.0))
    )
    net_return_by_trade = (
        frame.assign(trade_id=active_trade_ids)
        .loc[lambda df: df["trade_id"] > 0]
        .groupby("trade_id", sort=True)["strategy_return"]
        .apply(lambda series: float((1.0 + series.astype(float)).prod() - 1.0))
    )
    holding_period_by_trade = (
        frame.assign(trade_id=active_trade_ids)
        .loc[lambda df: df["trade_id"] > 0]
        .loc[lambda df: df["position"].astype(float) > 0.0]
        .groupby("trade_id", sort=True)
        .size()
    )

    trade_frame = (
        entry_rows.merge(exit_rows, on="trade_id", how="inner")
        .sort_values("trade_id")
        .assign(
            holding_period=lambda df: df["trade_id"].map(holding_period_by_trade).astype(int),
            trade_gross_return=lambda df: df["trade_id"].map(gross_return_by_trade).astype(float),
            trade_net_return=lambda df: df["trade_id"].map(net_return_by_trade).astype(float),
        )
    )
    trade_frame["cost_return_contribution"] = trade_frame["trade_gross_return"] - trade_frame["trade_net_return"]
    trade_frame["entry_datetime"] = trade_frame["entry_datetime"].map(str)
    trade_frame["exit_datetime"] = trade_frame["exit_datetime"].map(str)
    trade_frame["entry_price"] = trade_frame["entry_price"].astype(float)
    trade_frame["exit_price"] = trade_frame["exit_price"].astype(float)
    trade_frame["entry_target_position"] = trade_frame["entry_target_position"].astype(float)
    trade_frame["exit_target_position"] = trade_frame["exit_target_position"].astype(float)

    return [
        TradeRecord(
            entry_datetime=row.entry_datetime,
            exit_datetime=row.exit_datetime,
            entry_price=float(row.entry_price),
            exit_price=float(row.exit_price),
            holding_period=int(row.holding_period),
            trade_gross_return=float(row.trade_gross_return),
            trade_net_return=float(row.trade_net_return),
            cost_return_contribution=float(row.cost_return_contribution),
            entry_target_position=float(row.entry_target_position),
            exit_target_position=float(row.exit_target_position),
        )
        for row in trade_frame.itertuples(index=False)
    ]
