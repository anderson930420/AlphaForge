from __future__ import annotations

import pandas as pd

from alphaforge.backtest import run_backtest
from alphaforge.schemas import BacktestConfig


def test_backtest_produces_equity_curve_and_trade_log() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=5, freq="D"),
            "close": [100, 102, 104, 103, 105],
        }
    )
    target_positions = pd.Series([0.0, 1.0, 1.0, 0.0, 0.0])
    config = BacktestConfig(initial_capital=1000, fee_rate=0.0, slippage_rate=0.0, annualization_factor=252)

    equity_curve, trades = run_backtest(market_data, target_positions, config)

    assert "equity" in equity_curve.columns
    assert trades.shape[0] == 1
    assert trades.iloc[0]["entry_price"] == 104
    assert trades.iloc[0]["exit_price"] == 105
    assert equity_curve.iloc[-1]["equity"] > config.initial_capital


def test_backtest_returns_empty_trade_log_with_stable_columns() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=4, freq="D"),
            "close": [100, 101, 102, 103],
        }
    )
    target_positions = pd.Series([0.0, 0.0, 0.0, 0.0])
    config = BacktestConfig(initial_capital=1000, fee_rate=0.0, slippage_rate=0.0, annualization_factor=252)

    _, trades = run_backtest(market_data, target_positions, config)

    assert trades.empty
    assert trades.columns.tolist() == [
        "entry_time",
        "exit_time",
        "side",
        "quantity",
        "entry_price",
        "exit_price",
        "gross_return",
        "net_pnl",
    ]
