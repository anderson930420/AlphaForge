from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alphaforge.backtest import (
    BACKTEST_EQUITY_CURVE_COLUMNS,
    BACKTEST_TRADE_LOG_COLUMNS,
    build_execution_semantics_metadata,
    run_backtest,
)
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
    assert equity_curve["position"].tolist() == [0.0, 0.0, 1.0, 0.0]
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
    assert trades.iloc[0]["entry_datetime"] == "2024-01-02 00:00:00"
    assert trades.iloc[0]["exit_datetime"] == "2024-01-04 00:00:00"
    assert trades.iloc[0]["entry_price"] == 102
    assert trades.iloc[0]["exit_price"] == 105
    assert trades.iloc[0]["holding_period"] == 3
    assert trades.iloc[0]["entry_target_position"] == 1.0
    assert trades.iloc[0]["exit_target_position"] == 1.0


def test_backtest_forces_a_final_exit_for_an_open_trade() -> None:
    market_data = _make_market_data([100, 101, 103, 106, 108])
    target_positions = pd.Series([0.0, 1.0, 1.0, 1.0, 1.0])

    equity_curve, trades = run_backtest(market_data, target_positions, _make_config())

    assert equity_curve["position"].tolist() == [0.0, 0.0, 1.0, 1.0, 1.0]
    assert trades.shape[0] == 1
    assert trades.iloc[0]["entry_datetime"] == "2024-01-03 00:00:00"
    assert trades.iloc[0]["exit_datetime"] == "2024-01-05 00:00:00"
    assert trades.iloc[0]["exit_price"] == 108


def test_backtest_extracts_standard_entry_and_exit_transitions() -> None:
    market_data = _make_market_data([100, 101, 102, 103])
    target_positions = pd.Series([0.0, 1.0, 0.0, 0.0])

    equity_curve, trades = run_backtest(market_data, target_positions, _make_config())

    assert equity_curve["target_position"].tolist() == [0.0, 1.0, 0.0, 0.0]
    assert equity_curve["position"].tolist() == [0.0, 0.0, 1.0, 0.0]
    assert trades.shape[0] == 1
    assert trades.iloc[0]["entry_datetime"] == "2024-01-03 00:00:00"
    assert trades.iloc[0]["exit_datetime"] == "2024-01-04 00:00:00"


def test_backtest_extracts_return_based_trade_fields_for_one_trade() -> None:
    market_data = _make_market_data([100, 110, 121, 121])
    target_positions = pd.Series([0.0, 1.0, 1.0, 0.0])
    config = BacktestConfig(initial_capital=1000, fee_rate=0.01, slippage_rate=0.0, annualization_factor=252)

    _, trades = run_backtest(market_data, target_positions, config)

    assert trades.shape[0] == 1
    trade = trades.iloc[0]
    assert trade["entry_datetime"] == "2024-01-03 00:00:00"
    assert trade["exit_datetime"] == "2024-01-04 00:00:00"
    assert trade["entry_price"] == 121.0
    assert trade["exit_price"] == 121.0
    assert trade["holding_period"] == 2
    assert trade["trade_gross_return"] == pytest.approx(0.10, rel=1e-9)
    assert trade["trade_net_return"] == pytest.approx(0.09, rel=1e-9)
    assert trade["cost_return_contribution"] == pytest.approx(0.01, rel=1e-9)
    assert trade["entry_target_position"] == 1.0
    assert trade["exit_target_position"] == 0.0


def test_execution_semantics_metadata_is_explicit() -> None:
    metadata = build_execution_semantics_metadata()

    assert metadata == {
        "execution_semantics": "legacy_close_to_close_lagged",
        "position_rule": "position[t] = target_position[t-1]",
        "return_rule": "close_to_close",
        "position_bounds": [0.0, 1.0],
        "supports_shorting": False,
        "supports_leverage": False,
    }
