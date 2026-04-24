from __future__ import annotations

from pathlib import Path

from alphaforge.evidence import build_candidate_evidence_summary, build_walk_forward_evidence_summary
from alphaforge.policy import evaluate_candidate_policy, evaluate_walk_forward_policy
from alphaforge.schemas import BacktestConfig, DataSpec, ExperimentResult, MetricReport, SearchSummary, StrategySpec


def _make_result(
    short_window: int,
    long_window: int,
    *,
    total_return: float,
    annualized_return: float,
    sharpe_ratio: float,
    max_drawdown: float,
    score: float = 0.5,
) -> ExperimentResult:
    return ExperimentResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": short_window, "long_window": long_window}),
        backtest_config=BacktestConfig(initial_capital=100000.0, fee_rate=0.001, slippage_rate=0.0005, annualization_factor=252),
        metrics=MetricReport(
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=0.6,
            turnover=1.2,
            trade_count=4,
        ),
        score=score,
    )


def _make_search_summary(result: ExperimentResult) -> SearchSummary:
    return SearchSummary(
        strategy_name=result.strategy_spec.name,
        search_parameter_names=list(result.strategy_spec.parameters),
        attempted_combinations=1,
        valid_combinations=1,
        invalid_combinations=0,
        result_count=1,
        ranking_score="score",
        best_result=result,
        top_results=[result],
    )


def test_validation_policy_validates_complete_positive_evidence() -> None:
    train_result = _make_result(2, 4, total_return=0.1, annualized_return=0.12, sharpe_ratio=1.0, max_drawdown=-0.12)
    test_result = _make_result(2, 4, total_return=0.25, annualized_return=0.28, sharpe_ratio=1.4, max_drawdown=-0.08)
    evidence = build_candidate_evidence_summary(
        strategy_spec=train_result.strategy_spec,
        train_result=train_result,
        test_result=test_result,
        search_summary=_make_search_summary(train_result),
        benchmark_summary={"total_return": 0.1, "max_drawdown": -0.12},
    )

    decision = evaluate_candidate_policy(evidence, policy_scope="validate-search")

    assert decision.policy_name == "post_search_candidate_policy"
    assert decision.policy_scope == "validate-search"
    assert decision.verdict == "validated"
    assert decision.decision_reasons == [
        "evidence_complete",
        "out_of_sample_return_positive",
        "out_of_sample_sharpe_positive",
        "return_degradation_non_negative",
        "sharpe_degradation_non_negative",
        "max_drawdown_delta_non_negative",
        "benchmark_return_excess_non_negative",
    ]


def test_validation_policy_does_not_fail_on_lower_raw_test_return_when_annualized_return_is_not_degraded() -> None:
    train_result = _make_result(2, 4, total_return=0.25, annualized_return=0.10, sharpe_ratio=1.0, max_drawdown=-0.12)
    test_result = _make_result(2, 4, total_return=0.08, annualized_return=0.12, sharpe_ratio=1.1, max_drawdown=-0.08)
    evidence = build_candidate_evidence_summary(
        strategy_spec=train_result.strategy_spec,
        train_result=train_result,
        test_result=test_result,
        search_summary=_make_search_summary(train_result),
        benchmark_summary={"total_return": 0.02, "max_drawdown": -0.12},
    )

    decision = evaluate_candidate_policy(evidence, policy_scope="validate-search")

    assert test_result.metrics.total_return < train_result.metrics.total_return
    assert evidence.degradation_summary["return_degradation"] == test_result.metrics.annualized_return - train_result.metrics.annualized_return
    assert evidence.degradation_summary["return_degradation"] >= 0.0
    assert decision.verdict == "validated"


def test_validation_policy_rejects_clear_failure() -> None:
    train_result = _make_result(2, 4, total_return=0.2, annualized_return=0.22, sharpe_ratio=1.2, max_drawdown=-0.08)
    test_result = _make_result(2, 4, total_return=-0.05, annualized_return=-0.04, sharpe_ratio=-0.3, max_drawdown=-0.16)
    evidence = build_candidate_evidence_summary(
        strategy_spec=train_result.strategy_spec,
        train_result=train_result,
        test_result=test_result,
        search_summary=_make_search_summary(train_result),
        benchmark_summary={"total_return": 0.05, "max_drawdown": -0.1},
    )

    decision = evaluate_candidate_policy(evidence, policy_scope="validate-search")

    assert decision.verdict == "rejected"
    assert decision.decision_reasons == [
        "evidence_complete",
        "out_of_sample_return_non_positive",
    ]


def test_validation_policy_marks_partial_evidence_inconclusive() -> None:
    train_result = _make_result(2, 4, total_return=0.1, annualized_return=0.12, sharpe_ratio=1.0, max_drawdown=-0.12)
    evidence = build_candidate_evidence_summary(
        strategy_spec=train_result.strategy_spec,
        train_result=train_result,
        test_result=None,
        search_summary=_make_search_summary(train_result),
        benchmark_summary={"total_return": 0.1, "max_drawdown": -0.12},
    )

    decision = evaluate_candidate_policy(evidence, policy_scope="validate-search")

    assert decision.verdict == "inconclusive"
    assert decision.decision_reasons == ["missing_test_metrics"]


def test_walk_forward_policy_validates_complete_positive_aggregate() -> None:
    summary = build_walk_forward_evidence_summary(
        fold_count=3,
        validated_fold_count=3,
        skipped_fold_count=0,
        aggregate_test_metrics={
            "fold_count": 3,
            "mean_test_total_return": 0.12,
            "mean_test_sharpe_ratio": 1.1,
            "mean_test_max_drawdown": -0.05,
            "worst_test_max_drawdown": -0.12,
        },
        aggregate_benchmark_metrics={
            "fold_count": 3,
            "mean_benchmark_total_return": 0.08,
            "mean_benchmark_max_drawdown": -0.08,
            "mean_excess_return": 0.04,
        },
    )

    decision = evaluate_walk_forward_policy(summary)

    assert decision.policy_name == "post_search_candidate_policy"
    assert decision.policy_scope == "walk-forward"
    assert decision.verdict == "validated"
    assert decision.decision_reasons == [
        "fold_coverage_complete",
        "aggregate_return_positive",
        "aggregate_sharpe_positive",
        "aggregate_return_excess_non_negative",
        "aggregate_drawdown_non_worsening",
    ]


def test_walk_forward_policy_rejects_clear_failure() -> None:
    summary = build_walk_forward_evidence_summary(
        fold_count=2,
        validated_fold_count=2,
        skipped_fold_count=0,
        aggregate_test_metrics={
            "fold_count": 2,
            "mean_test_total_return": -0.03,
            "mean_test_sharpe_ratio": -0.2,
            "mean_test_max_drawdown": -0.14,
            "worst_test_max_drawdown": -0.2,
        },
        aggregate_benchmark_metrics={
            "fold_count": 2,
            "mean_benchmark_total_return": 0.02,
            "mean_benchmark_max_drawdown": -0.06,
            "mean_excess_return": -0.05,
        },
    )

    decision = evaluate_walk_forward_policy(summary)

    assert decision.verdict == "rejected"
    assert decision.decision_reasons == [
        "fold_coverage_complete",
        "aggregate_return_non_positive",
    ]


def test_walk_forward_policy_marks_incomplete_folds_inconclusive() -> None:
    summary = build_walk_forward_evidence_summary(
        fold_count=3,
        validated_fold_count=2,
        skipped_fold_count=1,
        aggregate_test_metrics={
            "fold_count": 3,
            "mean_test_total_return": 0.12,
            "mean_test_sharpe_ratio": 1.1,
            "mean_test_max_drawdown": -0.05,
            "worst_test_max_drawdown": -0.12,
        },
        aggregate_benchmark_metrics={
            "fold_count": 3,
            "mean_benchmark_total_return": 0.08,
            "mean_benchmark_max_drawdown": -0.08,
            "mean_excess_return": 0.04,
        },
    )

    decision = evaluate_walk_forward_policy(summary)

    assert decision.verdict == "inconclusive"
    assert decision.decision_reasons == ["fold_coverage_incomplete"]
