from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.backtest import (
    BACKTEST_EXECUTION_EVENT_COLUMNS,
    SIGNED_EXECUTION_SEMANTICS,
    build_execution_events,
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


def test_build_execution_events_returns_empty_frame_with_stable_columns_for_flat_book() -> None:
    config = BacktestConfig(initial_capital=1000, fee_rate=0.01, slippage_rate=0.02)
    equity_curve, _ = run_backtest(
        _make_market_data([100, 100, 100]),
        pd.Series([0.0, 0.0, 0.0]),
        config,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )

    events = build_execution_events(equity_curve, config, symbol="TEST")

    assert events.empty
    assert events.columns.tolist() == list(BACKTEST_EXECUTION_EVENT_COLUMNS)


def test_build_execution_events_classifies_signed_position_transitions() -> None:
    config = BacktestConfig(initial_capital=1000, fee_rate=0.01, slippage_rate=0.02)
    equity_curve, trades = run_backtest(
        _make_market_data([100, 100, 100, 100, 100, 100]),
        pd.Series([1.0, 0.5, -0.5, -1.0, 0.0, 0.0]),
        config,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )

    events = build_execution_events(equity_curve, config, symbol="TEST")

    assert trades.shape[0] == 2
    assert events.columns.tolist() == list(BACKTEST_EXECUTION_EVENT_COLUMNS)
    assert events["symbol"].tolist() == ["TEST"] * 5
    assert events["event_type"].tolist() == ["open", "reduce", "flip", "increase", "close"]
    assert events["previous_position"].tolist() == pytest.approx([0.0, 1.0, 0.5, -0.5, -1.0])
    assert events["target_position"].tolist() == pytest.approx([1.0, 0.5, -0.5, -1.0, 0.0])
    assert events["position_delta"].tolist() == pytest.approx([1.0, -0.5, -1.0, -0.5, 1.0])
    assert events["price"].tolist() == pytest.approx([100.0] * 5)
    assert events["notional_delta"].tolist() == pytest.approx([100.0, -50.0, -100.0, -50.0, 100.0])
    assert events["turnover"].tolist() == pytest.approx([1.0, 0.5, 1.0, 0.5, 1.0])
    assert events["fee"].tolist() == pytest.approx([0.01, 0.005, 0.01, 0.005, 0.01])
    assert events["slippage"].tolist() == pytest.approx([0.02, 0.01, 0.02, 0.01, 0.02])
    assert events["cost"].tolist() == pytest.approx([0.03, 0.015, 0.03, 0.015, 0.03])
    assert events["source"].tolist() == [SIGNED_EXECUTION_SEMANTICS] * 5


def test_build_execution_events_rejects_missing_required_columns() -> None:
    config = BacktestConfig(initial_capital=1000, fee_rate=0.0, slippage_rate=0.0)

    with pytest.raises(ValueError, match="Missing required execution-event columns"):
        build_execution_events(pd.DataFrame({"datetime": ["2024-01-01"]}), config)
