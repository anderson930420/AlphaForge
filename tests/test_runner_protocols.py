from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.runner_protocols import (
    build_validation_metadata,
    generate_walk_forward_folds,
    split_market_data_by_ratio,
    validate_train_windows,
)


def test_split_market_data_by_ratio_returns_chronological_segments() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=6, freq="D"),
            "close": [1, 2, 3, 4, 5, 6],
        }
    )

    train_data, test_data = split_market_data_by_ratio(market_data, 0.5)

    assert train_data["datetime"].tolist() == list(pd.date_range("2024-01-01", periods=3, freq="D"))
    assert test_data["datetime"].tolist() == list(pd.date_range("2024-01-04", periods=3, freq="D"))


def test_split_market_data_by_ratio_rejects_invalid_ratio() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=4, freq="D"),
            "close": [1, 2, 3, 4],
        }
    )

    with pytest.raises(ValueError, match="split_ratio"):
        split_market_data_by_ratio(market_data, 1.0)


def test_validate_train_windows_rejects_insufficient_history() -> None:
    train_data = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=3, freq="D")})

    with pytest.raises(ValueError, match="Train segment is too short"):
        validate_train_windows(train_data, {"long_window": [5]})


def test_generate_walk_forward_folds_returns_expected_boundaries() -> None:
    market_data = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=10, freq="D")})

    folds = generate_walk_forward_folds(market_data, train_size=4, test_size=2, step_size=2)

    assert folds == [(0, 4, 6), (2, 6, 8), (4, 8, 10)]


def test_build_validation_metadata_reports_split_ranges() -> None:
    train_data = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=3, freq="D")})
    test_data = pd.DataFrame({"datetime": pd.date_range("2024-01-04", periods=2, freq="D")})

    metadata = build_validation_metadata(train_data, test_data)

    assert metadata == {
        "train_rows": 3,
        "test_rows": 2,
        "train_start": "2024-01-01 00:00:00",
        "train_end": "2024-01-03 00:00:00",
        "test_start": "2024-01-04 00:00:00",
        "test_end": "2024-01-05 00:00:00",
    }
