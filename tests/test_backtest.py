from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alphaforge.backtest import BACKTEST_EQUITY_CURVE_COLUMNS, BACKTEST_TRADE_LOG_COLUMNS, run_backtest
from alphaforge.schemas import BacktestConfig


def _make_market_data(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=len(closes), freq="D"),
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [10 + index for index in range(len(closes))],
        }
    )


def _make_config() -> BacktestConfig:
    return BacktestConfig(initial_capital=1000, fee_rate=0.0, slippage_rate=0.0, annualization_factor=252)


def test_backtest_handles_empty_frame_with_stable_trade_log_columns() -> None:
    market_data = _make_market_data([])
    target_positions = pd.Series(dtype=float)

    equity_curve, trades = run_backtest(market_data, target_positions, _make_config())

    assert equity_curve.columns.tolist() == list(BACKTEST_EQUITY_CURVE_COLUMNS)
    assert equity_curve.empty
    assert trades.empty
    assert trades.columns.tolist() == list(BACKTEST_TRADE_LOG_COLUMNS)


def test_backtest_returns_empty_trade_log_when_always_flat() -> None:
    market_data = _make_market_data([100, 101, 102, 103])
    target_positions = pd.Series([0.0, 0.0, 0.0, 0.0])

    _, trades = run_backtest(market_data, target_positions, _make_config())

    assert trades.empty
    assert trades.columns.tolist() == list(BACKTEST_TRADE_LOG_COLUMNS)


def test_backtest_rejects_same_length_series_with_mismatched_index() -> None:
    market_data = _make_market_data([100, 101, 102, 103])
    target_positions = pd.Series([0.0, 1.0, 0.0, 0.0], index=[10, 11, 12, 13])

    with pytest.raises(ValueError, match="target_positions index alignment"):
        run_backtest(market_data, target_positions, _make_config())


def test_backtest_accepts_series_with_matching_index() -> None:
    market_data = _make_market_data([100, 101, 102, 103])
    target_positions = pd.Series([0.0, 1.0, 0.0, 0.0], index=market_data.index)

    equity_curve, trades = run_backtest(market_data, target_positions, _make_config())

    assert equity_curve["target_position"].tolist() == [0.0, 1.0, 0.0, 0.0]
    assert trades.shape[0] == 1


@pytest.mark.parametrize("target_positions", [[0.0, 1.0, 0.0, 0.0], np.array([0.0, 1.0, 0.0, 0.0])])
def test_backtest_accepts_list_like_target_positions_positionally(target_positions) -> None:
    market_data = _make_market_data([100, 101, 102, 103])

    equity_curve, trades = run_backtest(market_data, target_positions, _make_config())

    assert equity_curve["target_position"].tolist() == [0.0, 1.0, 0.0, 0.0]
    assert trades.shape[0] == 1


def test_backtest_rejects_target_position_length_mismatch() -> None:
    market_data = _make_market_data([100, 101, 102, 103])

    with pytest.raises(ValueError, match="target_positions length"):
        run_backtest(market_data, [0.0, 1.0, 0.0], _make_config())


def test_backtest_forces_a_final_exit_when_always_in_position() -> None:
    market_data = _make_market_data([100, 102, 104, 105])
    target_positions = pd.Series([1.0, 1.0, 1.0, 1.0])

    equity_curve, trades = run_backtest(market_data, target_positions, _make_config())

    assert equity_curve.columns.tolist() == list(BACKTEST_EQUITY_CURVE_COLUMNS)
    assert trades.shape[0] == 1
    assert trades.iloc[0]["entry_time"] == "2024-01-02 00:00:00"
    assert trades.iloc[0]["exit_time"] == "2024-01-04 00:00:00"
    assert trades.iloc[0]["entry_price"] == 102
    assert trades.iloc[0]["exit_price"] == 105
    assert trades.iloc[0]["quantity"] == 1.0


def test_backtest_forces_a_final_exit_for_an_open_trade() -> None:
    market_data = _make_market_data([100, 101, 103, 106, 108])
    target_positions = pd.Series([0.0, 1.0, 1.0, 1.0, 1.0])

    equity_curve, trades = run_backtest(market_data, target_positions, _make_config())

    assert equity_curve["position"].tolist() == [0.0, 0.0, 1.0, 1.0, 1.0]
    assert trades.shape[0] == 1
    assert trades.iloc[0]["entry_time"] == "2024-01-03 00:00:00"
    assert trades.iloc[0]["exit_time"] == "2024-01-05 00:00:00"
    assert trades.iloc[0]["exit_price"] == 108


def test_backtest_extracts_standard_entry_and_exit_transitions() -> None:
    market_data = _make_market_data([100, 101, 102, 103])
    target_positions = pd.Series([0.0, 1.0, 0.0, 0.0])

    equity_curve, trades = run_backtest(market_data, target_positions, _make_config())

    assert equity_curve["target_position"].tolist() == [0.0, 1.0, 0.0, 0.0]
    assert equity_curve["position"].tolist() == [0.0, 0.0, 1.0, 0.0]
    assert trades.shape[0] == 1
    assert trades.iloc[0]["entry_time"] == "2024-01-03 00:00:00"
    assert trades.iloc[0]["exit_time"] == "2024-01-04 00:00:00"
