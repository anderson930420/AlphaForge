from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.data_loader import load_market_data
from alphaforge.data_loader import split_holdout_data
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


def test_load_market_data_honors_custom_datetime_column(tmp_path) -> None:
    path = tmp_path / "custom_datetime.csv"
    pd.DataFrame(
        {
            "trade_date": ["2024-01-02", "2024-01-01"],
            "open": [2, 1],
            "high": [2, 1],
            "low": [2, 1],
            "close": [2, 1],
            "volume": [20, 10],
        }
    ).to_csv(path, index=False)

    loaded = load_market_data(DataSpec(path=path, datetime_column="trade_date"))

    assert loaded["datetime"].dt.strftime("%Y-%m-%d").tolist() == ["2024-01-01", "2024-01-02"]


def test_split_holdout_data_partitions_rows_and_preserves_order_and_columns() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=6, freq="D"),
            "open": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "high": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5],
            "low": [0.5, 1.5, 2.5, 3.5, 4.5, 5.5],
            "close": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "volume": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
        }
    )

    development_data, holdout_data = split_holdout_data(market_data, "2024-01-04")

    assert development_data["datetime"].dt.strftime("%Y-%m-%d").tolist() == ["2024-01-01", "2024-01-02", "2024-01-03"]
    assert holdout_data["datetime"].dt.strftime("%Y-%m-%d").tolist() == ["2024-01-04", "2024-01-05", "2024-01-06"]
    assert development_data.columns.tolist() == market_data.columns.tolist()
    assert holdout_data.columns.tolist() == market_data.columns.tolist()
    assert development_data["datetime"].is_monotonic_increasing
    assert holdout_data["datetime"].is_monotonic_increasing


def test_split_holdout_data_rejects_cutoff_that_removes_all_development_rows() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=3, freq="D"),
            "open": [1.0, 2.0, 3.0],
            "high": [1.0, 2.0, 3.0],
            "low": [1.0, 2.0, 3.0],
            "close": [1.0, 2.0, 3.0],
            "volume": [10.0, 11.0, 12.0],
        }
    )

    with pytest.raises(ValueError, match="development rows"):
        split_holdout_data(market_data, "2024-01-01")


def test_split_holdout_data_rejects_cutoff_that_removes_all_holdout_rows() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=3, freq="D"),
            "open": [1.0, 2.0, 3.0],
            "high": [1.0, 2.0, 3.0],
            "low": [1.0, 2.0, 3.0],
            "close": [1.0, 2.0, 3.0],
            "volume": [10.0, 11.0, 12.0],
        }
    )

    with pytest.raises(ValueError, match="holdout rows"):
        split_holdout_data(market_data, "2024-01-04")


def test_split_holdout_data_rejects_invalid_cutoff_and_missing_datetime() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=2, freq="D"),
            "open": [1.0, 2.0],
            "high": [1.0, 2.0],
            "low": [1.0, 2.0],
            "close": [1.0, 2.0],
            "volume": [10.0, 11.0],
        }
    )
    missing_datetime = market_data.drop(columns=["datetime"])

    with pytest.raises(ValueError, match="Invalid holdout_cutoff_date"):
        split_holdout_data(market_data, "not-a-date")

    with pytest.raises(ValueError, match="datetime column"):
        split_holdout_data(missing_datetime, "2024-01-02")
