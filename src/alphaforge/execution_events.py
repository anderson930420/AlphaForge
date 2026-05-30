from __future__ import annotations

from pathlib import Path

import pandas as pd

from .backtest import BACKTEST_EXECUTION_EVENT_COLUMNS, SIGNED_EXECUTION_SEMANTICS, build_execution_events
from .schemas import BacktestConfig

EXECUTION_EVENTS_FILENAME = "execution_events.csv"


def write_execution_events_artifact(
    output_dir: Path | str,
    equity_curve: pd.DataFrame,
    config: BacktestConfig,
    *,
    symbol: str = "UNKNOWN",
    source: str = SIGNED_EXECUTION_SEMANTICS,
) -> Path:
    """Write the signed execution-event artifact for a backtest equity curve.

    This is intentionally separate from ``trade_log.csv``. The trade log remains
    a position-segment summary, while ``execution_events.csv`` records realized
    rebalance events such as open, increase, reduce, flip, and close.
    """
    output_path = Path(output_dir) / EXECUTION_EVENTS_FILENAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    events = build_execution_events(equity_curve, config, symbol=symbol, source=source)
    events.reindex(columns=BACKTEST_EXECUTION_EVENT_COLUMNS).to_csv(output_path, index=False)
    return output_path
