from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture
def sample_market_csv(tmp_path: Path) -> Path:
    frame = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=8, freq="D"),
            "open": [100, 101, 102, 103, 104, 105, 106, 107],
            "high": [101, 103, 105, 104, 106, 108, 107, 109],
            "low": [99, 100, 101, 102, 103, 104, 105, 106],
            "close": [100, 102, 104, 103, 105, 107, 106, 108],
            "volume": [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700],
        }
    )
    path = tmp_path / "market.csv"
    frame.to_csv(path, index=False)
    return path
