from __future__ import annotations

import pytest

from alphaforge.scoring import passes_thresholds
from alphaforge.schemas import MetricReport
from alphaforge.search import build_strategy_specs


def test_build_strategy_specs_raises_when_all_ma_combinations_are_invalid() -> None:
    with pytest.raises(ValueError, match="No valid parameter combinations"):
        build_strategy_specs(
            "ma_crossover",
            {"short_window": [5, 6], "long_window": [3, 4]},
        )


def test_build_strategy_specs_skips_invalid_and_keeps_valid_combinations() -> None:
    specs = build_strategy_specs(
        "ma_crossover",
        {"short_window": [2, 4], "long_window": [3, 4, 5]},
    )

    assert [spec.parameters for spec in specs] == [
        {"short_window": 2, "long_window": 3},
        {"short_window": 2, "long_window": 4},
        {"short_window": 2, "long_window": 5},
        {"short_window": 4, "long_window": 5},
    ]


def test_passes_thresholds_allows_boundary_values() -> None:
    metrics = MetricReport(
        total_return=0.1,
        annualized_return=0.1,
        sharpe_ratio=1.0,
        max_drawdown=-0.2,
        win_rate=0.5,
        turnover=1.0,
        trade_count=3,
    )

    assert passes_thresholds(metrics, max_drawdown_cap=0.2, min_trade_count=3)
