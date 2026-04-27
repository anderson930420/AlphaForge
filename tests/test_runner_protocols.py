from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.schemas import StrategySpec
from alphaforge.runner_protocols import (
    build_strategy,
    build_validation_metadata,
    generate_walk_forward_folds,
    split_development_holdout_data,
    split_market_data_by_ratio,
    validate_train_windows,
)
from alphaforge.schemas import ResearchPeriod
from alphaforge.strategy.breakout import BreakoutStrategy
from alphaforge.strategy.ma_crossover import MovingAverageCrossoverStrategy


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


def test_split_development_holdout_data_returns_disjoint_periods() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=8, freq="D"),
            "close": range(8),
        }
    )

    development_data, holdout_data = split_development_holdout_data(
        market_data,
        ResearchPeriod(start="2024-01-02", end="2024-01-05"),
        ResearchPeriod(start="2024-01-06", end="2024-01-08"),
    )

    assert development_data["datetime"].tolist() == list(pd.date_range("2024-01-02", periods=4, freq="D"))
    assert holdout_data["datetime"].tolist() == list(pd.date_range("2024-01-06", periods=3, freq="D"))
    assert set(development_data["datetime"]).isdisjoint(set(holdout_data["datetime"]))
    assert development_data.attrs["research_period_role"] == "development"
    assert holdout_data.attrs["research_period_role"] == "final_holdout"


def test_split_development_holdout_data_rejects_overlapping_ranges() -> None:
    market_data = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=8, freq="D")})

    with pytest.raises(ValueError, match="must not overlap"):
        split_development_holdout_data(
            market_data,
            ResearchPeriod(start="2024-01-01", end="2024-01-05"),
            ResearchPeriod(start="2024-01-05", end="2024-01-08"),
        )


def test_split_development_holdout_data_rejects_empty_development_period() -> None:
    market_data = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=8, freq="D")})

    with pytest.raises(ValueError, match="development period contains no rows"):
        split_development_holdout_data(
            market_data,
            ResearchPeriod(start="2023-01-01", end="2023-01-31"),
            ResearchPeriod(start="2024-01-03", end="2024-01-08"),
        )


def test_split_development_holdout_data_rejects_empty_holdout_period() -> None:
    market_data = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=8, freq="D")})

    with pytest.raises(ValueError, match="holdout period contains no rows"):
        split_development_holdout_data(
            market_data,
            ResearchPeriod(start="2024-01-01", end="2024-01-05"),
            ResearchPeriod(start="2025-01-01", end="2025-01-31"),
        )


def test_validate_train_windows_rejects_insufficient_history() -> None:
    train_data = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=3, freq="D")})

    with pytest.raises(ValueError, match="Train segment is too short"):
        validate_train_windows("ma_crossover", train_data, {"long_window": [5]})


def test_validate_train_windows_rejects_breakout_insufficient_history() -> None:
    train_data = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=3, freq="D")})

    with pytest.raises(ValueError, match="lookback_window"):
        validate_train_windows("breakout", train_data, {"lookback_window": [5]})


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


def test_build_strategy_dispatches_supported_families() -> None:
    ma_strategy = build_strategy(
        StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 3})
    )
    breakout_strategy = build_strategy(
        StrategySpec(name="breakout", parameters={"lookback_window": 5})
    )

    assert isinstance(ma_strategy, MovingAverageCrossoverStrategy)
    assert isinstance(breakout_strategy, BreakoutStrategy)
