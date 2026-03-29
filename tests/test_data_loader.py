from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.data_loader import load_market_data
from alphaforge.schemas import DataSpec


def test_load_market_data_standardizes_and_sorts(tmp_path) -> None:
    frame = pd.DataFrame(
        {
            "Date": ["2024-01-02", "2024-01-01", "2024-01-01", "2024-01-03"],
            "Open": [2, 1, 9, 3],
            "High": [2, 1, 9, 3],
            "Low": [2, 1, 9, 3],
            "Close": [2, 1, 9, 3],
            "Volume": [20, None, 99, 30],
        }
    )
    path = tmp_path / "data.csv"
    frame.to_csv(path, index=False)

    loaded = load_market_data(DataSpec(path=path, symbol="TEST"))

    assert list(loaded.columns) == ["datetime", "open", "high", "low", "close", "volume"]
    assert loaded["datetime"].is_monotonic_increasing
    assert len(loaded) == 3
    assert loaded.iloc[0]["close"] == 9
    assert loaded.iloc[0]["volume"] == 99


def test_load_market_data_requires_ohlcv_columns(tmp_path) -> None:
    path = tmp_path / "broken.csv"
    pd.DataFrame({"datetime": ["2024-01-01"], "close": [1]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="Missing required columns"):
        load_market_data(DataSpec(path=path))
