from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.data_loader import load_market_data
from alphaforge.data_loader import split_holdout_data
from alphaforge.schemas import DataSpec


def test_load_market_data_standardizes_sorts_and_records_quality_summary(tmp_path) -> None:
    frame = pd.DataFrame(
        {
            "Date": ["2024-01-02", "2024-01-01", "2024-01-04", "2024-01-03"],
            "Open": [2, 1, 4, 3],
            "High": [2, 1, 4, 3],
            "Low": [2, 1, 4, 3],
            "Close": [2, 1, 4, 3],
            "Volume": [20, None, 40, 30],
        }
    )
    path = tmp_path / "data.csv"
    frame.to_csv(path, index=False)

    loaded = load_market_data(DataSpec(path=path, symbol="TEST"))

    assert list(loaded.columns) == ["datetime", "open", "high", "low", "close", "volume"]
    assert loaded["datetime"].is_monotonic_increasing
    assert loaded["datetime"].is_unique
    assert len(loaded) == 4
    assert loaded.iloc[0]["close"] == 1
    assert loaded.iloc[0]["volume"] == 0.0
    assert loaded.attrs["missing_data_policy"].startswith(
        "Drop rows with missing datetime or OHLC values; reject duplicate datetimes; and fill missing volume with 0."
    )
    assert loaded.attrs["data_quality_summary"] == {
        "required_columns": ["datetime", "open", "high", "low", "close", "volume"],
        "canonical_column_order": ["datetime", "open", "high", "low", "close", "volume"],
        "datetime_policy": "parse_sort_fail_on_duplicate",
        "duplicate_datetime_policy": "fail",
        "missing_ohlc_policy": "fail",
        "missing_volume_policy": "fill_zero",
        "missing_data_policy": loaded.attrs["missing_data_policy"],
        "source_row_count": 4,
        "duplicate_row_count": 0,
        "accepted_row_count": 4,
        "volume_missing_row_count": 1,
    }


def test_load_market_data_requires_ohlcv_columns(tmp_path) -> None:
    path = tmp_path / "broken.csv"
    pd.DataFrame({"datetime": ["2024-01-01"], "close": [1]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="Missing required columns"):
        load_market_data(DataSpec(path=path))


def test_load_market_data_rejects_missing_datetime_values(tmp_path) -> None:
    path = tmp_path / "missing_datetime.csv"
    pd.DataFrame(
        {
            "datetime": [None],
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "close": [1.0],
            "volume": [10.0],
        }
    ).to_csv(path, index=False)

    with pytest.raises(ValueError, match="datetime column contains missing values"):
        load_market_data(DataSpec(path=path))


def test_load_market_data_rejects_duplicate_datetime_values(tmp_path) -> None:
    path = tmp_path / "duplicate_datetime.csv"
    pd.DataFrame(
        {
            "datetime": ["2024-01-01", "2024-01-01", "2024-01-02"],
            "open": [1.0, 9.0, 2.0],
            "high": [1.0, 9.0, 2.0],
            "low": [1.0, 9.0, 2.0],
            "close": [1.0, 9.0, 2.0],
            "volume": [10.0, 90.0, 20.0],
        }
    ).to_csv(path, index=False)

    with pytest.raises(ValueError, match="duplicate datetime values are not allowed"):
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


def test_load_market_data_fills_missing_volume_explicitly(tmp_path) -> None:
    path = tmp_path / "missing_volume.csv"
    pd.DataFrame(
        {
            "datetime": ["2024-01-01", "2024-01-02"],
            "open": [1.0, 2.0],
            "high": [1.5, 2.5],
            "low": [0.5, 1.5],
            "close": [1.0, 2.0],
            "volume": [None, 10.0],
        }
    ).to_csv(path, index=False)

    loaded = load_market_data(DataSpec(path=path))

    assert loaded["volume"].tolist() == [0.0, 10.0]
    assert loaded.attrs["data_quality_summary"]["missing_volume_policy"] == "fill_zero"
    assert loaded.attrs["data_quality_summary"]["volume_missing_row_count"] == 1


@pytest.mark.parametrize("missing_column", ["open", "high", "low", "close"])
def test_load_market_data_rejects_missing_ohlc_values(tmp_path, missing_column: str) -> None:
    path = tmp_path / f"missing_{missing_column}.csv"
    frame = pd.DataFrame(
        {
            "datetime": ["2024-01-01"],
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "close": [1.0],
            "volume": [10.0],
        }
    )
    frame.loc[0, missing_column] = None
    frame.to_csv(path, index=False)

    with pytest.raises(ValueError, match="Missing OHLC values are not allowed"):
        load_market_data(DataSpec(path=path))


@pytest.mark.parametrize("column,value", [("open", float("inf")), ("close", float("-inf"))])
def test_load_market_data_rejects_non_finite_ohlc_values(tmp_path, column: str, value: float) -> None:
    path = tmp_path / f"non_finite_{column}.csv"
    frame = pd.DataFrame(
        {
            "datetime": ["2024-01-01"],
            "open": [1.0],
            "high": [1.5],
            "low": [0.5],
            "close": [1.0],
            "volume": [10.0],
        }
    )
    frame.loc[0, column] = value
    frame.to_csv(path, index=False)

    with pytest.raises(ValueError, match="OHLC values must be finite"):
        load_market_data(DataSpec(path=path))


@pytest.mark.parametrize("column,value", [("open", 0.0), ("close", -1.0)])
def test_load_market_data_rejects_non_positive_ohlc_values(tmp_path, column: str, value: float) -> None:
    path = tmp_path / f"non_positive_{column}.csv"
    frame = pd.DataFrame(
        {
            "datetime": ["2024-01-01"],
            "open": [1.0],
            "high": [1.5],
            "low": [0.5],
            "close": [1.0],
            "volume": [10.0],
        }
    )
    frame.loc[0, column] = value
    frame.to_csv(path, index=False)

    with pytest.raises(ValueError, match="OHLC values must be positive"):
        load_market_data(DataSpec(path=path))


@pytest.mark.parametrize(
    ("mutations", "message"),
    [
        ({"high": 0.4, "low": 0.5}, "high must be greater than or equal to low"),
        ({"high": 0.9}, "high must be greater than or equal to open"),
        ({"high": 1.0}, "high must be greater than or equal to close"),
        ({"low": 1.1}, "low must be less than or equal to open"),
        ({"open": 2.0, "high": 2.5, "low": 1.3}, "low must be less than or equal to close"),
    ],
)
def test_load_market_data_rejects_invalid_ohlc_relations(tmp_path, mutations: dict[str, float], message: str) -> None:
    path = tmp_path / "relation_violation.csv"
    frame = pd.DataFrame(
        {
            "datetime": ["2024-01-01"],
            "open": [1.0],
            "high": [1.5],
            "low": [0.5],
            "close": [1.2],
            "volume": [10.0],
        }
    )
    for column, value in mutations.items():
        frame.loc[0, column] = value
    frame.to_csv(path, index=False)

    with pytest.raises(ValueError, match=message):
        load_market_data(DataSpec(path=path))


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


def test_split_holdout_data_preserves_loader_metadata() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=4, freq="D"),
            "open": [1.0, 2.0, 3.0, 4.0],
            "high": [1.5, 2.5, 3.5, 4.5],
            "low": [0.5, 1.5, 2.5, 3.5],
            "close": [1.0, 2.0, 3.0, 4.0],
            "volume": [10.0, 11.0, 12.0, 13.0],
        }
    )
    market_data.attrs["missing_data_policy"] = "test-policy"
    market_data.attrs["data_quality_summary"] = {"duplicate_datetime_policy": "fail"}

    development_data, holdout_data = split_holdout_data(market_data, "2024-01-03")

    assert development_data.attrs["missing_data_policy"] == "test-policy"
    assert holdout_data.attrs["missing_data_policy"] == "test-policy"
    assert development_data.attrs["data_quality_summary"] == {"duplicate_datetime_policy": "fail"}
    assert holdout_data.attrs["data_quality_summary"] == {"duplicate_datetime_policy": "fail"}


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
