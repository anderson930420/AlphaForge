from __future__ import annotations

from pathlib import Path

import pytest

from alphaforge.scoring import passes_thresholds, rank_results, score_metrics, select_best_result, select_top_results
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


def test_build_strategy_specs_supports_breakout_candidates() -> None:
    specs = build_strategy_specs("breakout", {"lookback_window": [2, 4]})

    assert [spec.parameters for spec in specs] == [
        {"lookback_window": 2},
        {"lookback_window": 4},
    ]


def test_evaluate_strategy_search_space_reports_attempted_valid_and_invalid_counts_for_breakout() -> None:
    evaluation = evaluate_strategy_search_space("breakout", {"lookback_window": [2, 0]})

    assert evaluation.attempted_combination_count == 2
    assert evaluation.valid_combination_count == 1
    assert evaluation.invalid_combination_count == 1
    assert list(evaluation.invalid_combinations) == [{"lookback_window": 0}]


def test_evaluate_strategy_search_space_rejects_unsupported_strategy_family() -> None:
    with pytest.raises(ValueError, match="Unsupported strategy"):
        evaluate_strategy_search_space("unknown_strategy", {"lookback_window": [2]})


def test_passes_thresholds_allows_boundary_values() -> None:
    metrics = MetricReport(
        total_return=0.1,
        annualized_return=0.1,
        sharpe_ratio=1.0,
        max_drawdown=-0.2,
        win_rate=0.5,
        turnover=1.0,
        trade_count=3, bar_count=1)

    assert passes_thresholds(metrics, max_drawdown_cap=0.2, min_trade_count=3)


def test_select_best_result_returns_highest_ranked_passing_result() -> None:
    lower = ExperimentResult(
        data_spec=DataSpec(path=Path(__file__)),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 2, bar_count=1),
        score=0.4,
    )
    higher = ExperimentResult(
        data_spec=DataSpec(path=Path(__file__)),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 3, "long_window": 5}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.2, 0.2, 1.5, -0.05, 1.0, 1.2, 3, bar_count=1),
        score=0.8,
    )

    assert select_best_result([lower, higher]) == higher


def test_rank_results_breaks_score_ties_deterministically_by_strategy_parameters() -> None:
    first = ExperimentResult(
        data_spec=DataSpec(path=Path(__file__)),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 3, "long_window": 6}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 2, bar_count=1),
        score=0.7,
    )
    second = ExperimentResult(
        data_spec=DataSpec(path=Path(__file__)),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 5}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 2, bar_count=1),
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
            metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 2, bar_count=1),
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


def test_score_metrics_normalizes_turnover_penalty_by_bar_count() -> None:
    short_window_metrics = MetricReport(
        total_return=0.2,
        annualized_return=0.3,
        sharpe_ratio=1.0,
        max_drawdown=-0.08,
        win_rate=0.6,
        turnover=10.0,
        trade_count=4,
        bar_count=10,
    )
    long_window_metrics = MetricReport(
        total_return=0.2,
        annualized_return=0.3,
        sharpe_ratio=1.0,
        max_drawdown=-0.08,
        win_rate=0.6,
        turnover=20.0,
        trade_count=4,
        bar_count=20,
    )

    assert score_metrics(short_window_metrics) == score_metrics(long_window_metrics)


def test_score_metrics_rejects_invalid_bar_count() -> None:
    invalid_metrics = MetricReport.__new__(MetricReport)
    object.__setattr__(invalid_metrics, "total_return", 0.2)
    object.__setattr__(invalid_metrics, "annualized_return", 0.3)
    object.__setattr__(invalid_metrics, "sharpe_ratio", 1.0)
    object.__setattr__(invalid_metrics, "max_drawdown", -0.08)
    object.__setattr__(invalid_metrics, "win_rate", 0.6)
    object.__setattr__(invalid_metrics, "turnover", 10.0)
    object.__setattr__(invalid_metrics, "trade_count", 4)
    object.__setattr__(invalid_metrics, "bar_count", 0)

    with pytest.raises(ValueError, match="bar_count must be positive for scoring"):
        score_metrics(invalid_metrics)
