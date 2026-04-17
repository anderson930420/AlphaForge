from __future__ import annotations

from pathlib import Path

import pytest

from alphaforge.scoring import passes_thresholds, rank_results, select_best_result, select_top_results
from alphaforge.schemas import BacktestConfig, DataSpec, ExperimentResult, MetricReport, StrategySpec
from alphaforge.search import build_strategy_specs, evaluate_strategy_search_space


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


def test_evaluate_strategy_search_space_reports_attempted_valid_and_invalid_counts() -> None:
    evaluation = evaluate_strategy_search_space(
        "ma_crossover",
        {"short_window": [2, 4], "long_window": [3, 4, 5]},
    )

    assert evaluation.attempted_combination_count == 6
    assert evaluation.valid_combination_count == 4
    assert evaluation.invalid_combination_count == 2
    assert list(evaluation.invalid_combinations) == [
        {"short_window": 4, "long_window": 3},
        {"short_window": 4, "long_window": 4},
    ]


def test_evaluate_strategy_search_space_rejects_missing_ma_parameter_grid_keys() -> None:
    with pytest.raises(ValueError, match="requires parameter grids for: long_window"):
        evaluate_strategy_search_space("ma_crossover", {"short_window": [2, 3]})


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


def test_select_best_result_returns_highest_ranked_passing_result() -> None:
    lower = ExperimentResult(
        data_spec=DataSpec(path=Path(__file__)),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 2),
        score=0.4,
    )
    higher = ExperimentResult(
        data_spec=DataSpec(path=Path(__file__)),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 3, "long_window": 5}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.2, 0.2, 1.5, -0.05, 1.0, 1.2, 3),
        score=0.8,
    )

    assert select_best_result([lower, higher]) == higher


def test_rank_results_breaks_score_ties_deterministically_by_strategy_parameters() -> None:
    first = ExperimentResult(
        data_spec=DataSpec(path=Path(__file__)),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 3, "long_window": 6}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 2),
        score=0.7,
    )
    second = ExperimentResult(
        data_spec=DataSpec(path=Path(__file__)),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 5}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 2),
        score=0.7,
    )

    ranked = rank_results([first, second])

    assert [result.strategy_spec.parameters for result in ranked] == [
        {"short_window": 2, "long_window": 5},
        {"short_window": 3, "long_window": 6},
    ]


def test_select_top_results_returns_prefix_of_canonical_ranking() -> None:
    results = [
        ExperimentResult(
            data_spec=DataSpec(path=Path(__file__)),
            strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": short_window, "long_window": long_window}),
            backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
            metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 2),
            score=score,
        )
        for short_window, long_window, score in [
            (2, 5, 0.9),
            (3, 6, 0.8),
            (4, 7, 0.7),
        ]
    ]

    top_results = select_top_results(results, limit=2)

    assert [result.score for result in top_results] == [0.9, 0.8]
    assert select_best_result(results) == top_results[0]
