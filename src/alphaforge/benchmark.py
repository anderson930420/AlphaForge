from __future__ import annotations

"""Benchmark helpers for AlphaForge evaluation windows.

This module owns simple benchmark construction for already-loaded market data.
It does not run strategies, compute strategy metrics, or assemble reports.
"""

from typing import TypedDict

import pandas as pd


class BenchmarkSummary(TypedDict):
    total_return: float
    max_drawdown: float


def build_buy_and_hold_equity_curve(
    market_data: pd.DataFrame,
    initial_capital: float,
) -> pd.DataFrame:
    """Construct a buy-and-hold equity curve over the provided close series."""
    _validate_benchmark_input(market_data)

    close_values = market_data["close"].astype(float)
    starting_close = float(close_values.iloc[0])
    if starting_close <= 0.0:
        raise ValueError("close prices must start above zero for buy-and-hold benchmark construction")

    benchmark_equity = initial_capital * (close_values / starting_close)
    return pd.DataFrame(
        {
            "datetime": pd.to_datetime(market_data["datetime"]),
            "equity": benchmark_equity.astype(float),
        }
    )


def summarize_buy_and_hold(
    market_data: pd.DataFrame,
    initial_capital: float,
) -> BenchmarkSummary:
    """Compute a compact buy-and-hold summary for the same evaluation window."""
    benchmark_curve = build_buy_and_hold_equity_curve(market_data, initial_capital)
    equity_values = benchmark_curve["equity"].astype(float)
    drawdown = _compute_drawdown_series(equity_values)
    total_return = float((equity_values.iloc[-1] / equity_values.iloc[0]) - 1.0)
    max_drawdown = float(drawdown.min())
    return {
        "total_return": total_return,
        "max_drawdown": max_drawdown,
    }


def _validate_benchmark_input(market_data: pd.DataFrame) -> None:
    required_columns = ("datetime", "close")
    missing_columns = [column for column in required_columns if column not in market_data.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Market data is missing required columns for buy-and-hold benchmark: {missing}")
    if market_data.empty:
        raise ValueError("Market data is empty and cannot be used for buy-and-hold benchmark construction")


def _compute_drawdown_series(equity: pd.Series) -> pd.Series:
    equity_values = equity.astype(float)
    running_peak = equity_values.cummax()
    return (equity_values / running_peak) - 1.0
