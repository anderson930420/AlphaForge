from __future__ import annotations

from pathlib import Path

from alphaforge.evidence import (
    build_candidate_evidence_summary,
    build_walk_forward_evidence_summary,
    derive_candidate_verdict,
)
from alphaforge.schemas import BacktestConfig, DataSpec, ExperimentResult, MetricReport, SearchSummary, StrategySpec


def _make_result(short_window: int, long_window: int, score: float) -> ExperimentResult:
    return ExperimentResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": short_window, "long_window": long_window}),
        backtest_config=BacktestConfig(initial_capital=100000.0, fee_rate=0.001, slippage_rate=0.0005, annualization_factor=252),
        metrics=MetricReport(
            total_return=0.2,
            annualized_return=0.3,
            sharpe_ratio=1.4,
            max_drawdown=-0.08,
            win_rate=0.6,
            turnover=1.2,
            trade_count=4,
        ),
        score=score,
    )


def test_derive_candidate_verdict_covers_small_vocab() -> None:
    assert derive_candidate_verdict(has_search_context=True) == "candidate"
    assert derive_candidate_verdict(has_search_context=True, has_train_metrics=True, has_test_metrics=True) == "validated"
    assert derive_candidate_verdict(has_train_metrics=True, has_test_metrics=True, fold_count=0) == "inconclusive"
    assert derive_candidate_verdict(is_rejected=True) == "rejected"


def test_build_candidate_evidence_summary_records_degradation_and_search_context() -> None:
    best_result = _make_result(2, 4, 0.9)
    search_summary = SearchSummary(
        strategy_name="ma_crossover",
        search_parameter_names=["short_window", "long_window"],
        attempted_combinations=4,
        valid_combinations=4,
        invalid_combinations=0,
        result_count=4,
        ranking_score="score",
        best_result=best_result,
        top_results=[best_result],
    )
    train_result = _make_result(2, 4, 0.9)
    test_result = ExperimentResult(
        data_spec=train_result.data_spec,
        strategy_spec=train_result.strategy_spec,
        backtest_config=train_result.backtest_config,
        metrics=MetricReport(
            total_return=0.1,
            annualized_return=0.12,
            sharpe_ratio=1.1,
            max_drawdown=-0.12,
            win_rate=0.5,
            turnover=0.8,
            trade_count=2,
        ),
        score=0.4,
    )

    evidence = build_candidate_evidence_summary(
        strategy_spec=train_result.strategy_spec,
        train_result=train_result,
        test_result=test_result,
        search_summary=search_summary,
        benchmark_summary={"total_return": 0.05, "max_drawdown": -0.04},
        artifact_paths={"validation_summary_path": "/tmp/validation_summary.json"},
    )

    assert evidence.strategy_name == "ma_crossover"
    assert evidence.strategy_parameters == {"short_window": 2, "long_window": 4}
    assert evidence.verdict == "validated"
    assert evidence.search_rank == 1
    assert evidence.search_result_count == 4
    assert evidence.search_ranking_score == "score"
    assert evidence.search_score == 0.9
    assert evidence.degradation_summary == {
        "return_degradation": -0.1,
        "sharpe_degradation": -0.2999999999999998,
        "max_drawdown_delta": -0.039999999999999994,
    }
    assert evidence.benchmark_relative_summary == {
        "test_total_return": 0.1,
        "benchmark_total_return": 0.05,
        "return_excess": 0.05,
        "test_max_drawdown": -0.12,
        "benchmark_max_drawdown": -0.04,
        "max_drawdown_gap": -0.07999999999999999,
    }
    assert evidence.artifact_paths == {"validation_summary_path": "/tmp/validation_summary.json"}


def test_build_walk_forward_evidence_summary_records_fold_counts_and_artifacts() -> None:
    summary = build_walk_forward_evidence_summary(
        fold_count=3,
        validated_fold_count=3,
        skipped_fold_count=0,
        aggregate_test_metrics={"fold_count": 3, "mean_test_total_return": 0.12},
        aggregate_benchmark_metrics={"fold_count": 3, "mean_benchmark_total_return": 0.08},
        artifact_paths={"walk_forward_summary_path": "/tmp/walk_forward_summary.json", "fold_results_path": "/tmp/fold_results.csv"},
    )

    assert summary.verdict == "validated"
    assert summary.fold_count == 3
    assert summary.validated_fold_count == 3
    assert summary.skipped_fold_count == 0
    assert summary.aggregate_test_metrics == {"fold_count": 3, "mean_test_total_return": 0.12}
    assert summary.aggregate_benchmark_metrics == {"fold_count": 3, "mean_benchmark_total_return": 0.08}
    assert summary.artifact_paths == {
        "walk_forward_summary_path": "/tmp/walk_forward_summary.json",
        "fold_results_path": "/tmp/fold_results.csv",
    }
