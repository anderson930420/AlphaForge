from __future__ import annotations

import pandas as pd

from alphaforge.backtest import BACKTEST_EQUITY_CURVE_COLUMNS, BACKTEST_TRADE_LOG_COLUMNS, run_backtest
from alphaforge.schemas import BacktestConfig


def test_backtest_produces_equity_curve_and_trade_log() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=5, freq="D"),
            "open": [100, 102, 104, 103, 105],
            "high": [100, 102, 104, 103, 105],
            "low": [100, 102, 104, 103, 105],
            "close": [100, 102, 104, 103, 105],
            "volume": [10, 11, 12, 13, 14],
        }
    )
    target_positions = pd.Series([0.0, 1.0, 1.0, 0.0, 0.0])
    config = BacktestConfig(initial_capital=1000, fee_rate=0.0, slippage_rate=0.0, annualization_factor=252)

    equity_curve, trades = run_backtest(market_data, target_positions, config)

    assert equity_curve.columns.tolist() == list(BACKTEST_EQUITY_CURVE_COLUMNS)
    assert trades.shape[0] == 1
    assert trades.iloc[0]["entry_price"] == 104
    assert trades.iloc[0]["exit_price"] == 105
    assert equity_curve.iloc[-1]["equity"] > config.initial_capital


def test_backtest_returns_empty_trade_log_with_stable_columns() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=4, freq="D"),
            "open": [100, 101, 102, 103],
            "high": [100, 101, 102, 103],
            "low": [100, 101, 102, 103],
            "close": [100, 101, 102, 103],
            "volume": [10, 11, 12, 13],
        }
    )
    target_positions = pd.Series([0.0, 0.0, 0.0, 0.0])
    config = BacktestConfig(initial_capital=1000, fee_rate=0.0, slippage_rate=0.0, annualization_factor=252)

    _, trades = run_backtest(market_data, target_positions, config)

    assert trades.empty
    assert trades.columns.tolist() == list(BACKTEST_TRADE_LOG_COLUMNS)


def test_backtest_applies_target_positions_on_next_bar() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=4, freq="D"),
            "open": [100, 101, 102, 103],
            "high": [100, 101, 102, 103],
            "low": [100, 101, 102, 103],
            "close": [100, 101, 102, 103],
            "volume": [10, 11, 12, 13],
        }
    )
    target_positions = pd.Series([0.0, 1.0, 0.0, 0.0])
    config = BacktestConfig(initial_capital=1000, fee_rate=0.0, slippage_rate=0.0, annualization_factor=252)

    equity_curve, trades = run_backtest(market_data, target_positions, config)

    assert equity_curve["target_position"].tolist() == [0.0, 1.0, 0.0, 0.0]
    assert equity_curve["position"].tolist() == [0.0, 0.0, 1.0, 0.0]
    assert trades.shape[0] == 1
    assert trades.iloc[0]["entry_time"] == "2024-01-03 00:00:00"
    assert trades.iloc[0]["exit_time"] == "2024-01-04 00:00:00"
