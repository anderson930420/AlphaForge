from __future__ import annotations

from pathlib import Path

import pandas as pd

from alphaforge.backtest import BACKTEST_EXECUTION_EVENT_COLUMNS, SIGNED_EXECUTION_SEMANTICS, run_backtest
from alphaforge.execution_events import EXECUTION_EVENTS_FILENAME, write_execution_events_artifact
from alphaforge.schemas import BacktestConfig


def _market_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=4, freq="D"),
            "open": [100, 100, 100, 100],
            "high": [100, 100, 100, 100],
            "low": [100, 100, 100, 100],
            "close": [100, 100, 100, 100],
            "volume": [10, 11, 12, 13],
        }
    )


def test_write_execution_events_artifact(tmp_path: Path) -> None:
    config = BacktestConfig(initial_capital=1000, fee_rate=0.01, slippage_rate=0.02)
    equity_curve, _ = run_backtest(
        _market_data(),
        pd.Series([1.0, -1.0, 0.0, 0.0]),
        config,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )

    path = write_execution_events_artifact(tmp_path, equity_curve, config, symbol="TEST")

    assert path == tmp_path / EXECUTION_EVENTS_FILENAME
    events = pd.read_csv(path)
    assert events.columns.tolist() == list(BACKTEST_EXECUTION_EVENT_COLUMNS)
    assert events["event_type"].tolist() == ["open", "flip", "close"]
    assert events["symbol"].tolist() == ["TEST", "TEST", "TEST"]
