from __future__ import annotations

from typing import Any

from .benchmark import normalize_benchmark_summary
from .schemas import (
    CandidateEvidenceSummary,
    CandidateVerdict,
    ExperimentResult,
    MetricReport,
    SearchSummary,
    StrategySpec,
    WalkForwardEvidenceSummary,
)


def derive_candidate_verdict(
    *,
    has_search_context: bool = False,
    has_train_metrics: bool = False,
    has_test_metrics: bool = False,
    fold_count: int | None = None,
    is_rejected: bool = False,
) -> CandidateVerdict:
    if is_rejected:
        return "rejected"
    if has_train_metrics and has_test_metrics:
        if fold_count is not None and fold_count <= 0:
            return "inconclusive"
        return "validated"
    if has_search_context:
        return "candidate"
    return "inconclusive"


def build_candidate_evidence_summary(
    *,
    strategy_spec: StrategySpec,
    train_result: ExperimentResult | None,
    test_result: ExperimentResult | None,
    search_summary: SearchSummary | None = None,
    benchmark_summary: dict[str, float] | None = None,
    artifact_paths: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
    is_rejected: bool = False,
) -> CandidateEvidenceSummary:
    train_metrics = train_result.metrics if train_result is not None else None
    test_metrics = test_result.metrics if test_result is not None else None
    verdict = derive_candidate_verdict(
        has_search_context=search_summary is not None,
        has_train_metrics=train_metrics is not None,
        has_test_metrics=test_metrics is not None,
        is_rejected=is_rejected,
    )
    search_rank, search_result_count, search_ranking_score, search_score = _build_search_context(strategy_spec, search_summary)
    benchmark_relative_summary = _build_benchmark_relative_summary(test_result, benchmark_summary)
    degradation_summary = _build_degradation_summary(train_metrics, test_metrics)
    return CandidateEvidenceSummary(
        strategy_name=strategy_spec.name,
        strategy_parameters=dict(strategy_spec.parameters),
        verdict=verdict,
        search_rank=search_rank,
        search_result_count=search_result_count,
        search_ranking_score=search_ranking_score,
        search_score=search_score,
        train_metrics=train_metrics,
        test_metrics=test_metrics,
        benchmark_relative_summary=benchmark_relative_summary,
        degradation_summary=degradation_summary,
        artifact_paths=dict(artifact_paths or {}),
        metadata=dict(metadata or {}),
    )


def build_walk_forward_evidence_summary(
    *,
    fold_count: int,
    aggregate_test_metrics: dict[str, float | int],
    aggregate_benchmark_metrics: dict[str, float | int],
    validated_fold_count: int | None = None,
    skipped_fold_count: int | None = None,
    artifact_paths: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
    is_rejected: bool = False,
) -> WalkForwardEvidenceSummary:
    validated_fold_count = fold_count if validated_fold_count is None else validated_fold_count
    skipped_fold_count = 0 if skipped_fold_count is None else skipped_fold_count
    verdict = derive_candidate_verdict(
        has_train_metrics=True,
        has_test_metrics=True,
        fold_count=fold_count,
        is_rejected=is_rejected,
    )
    if fold_count == 0 or skipped_fold_count > 0 or validated_fold_count <= 0:
        verdict = "inconclusive"
    return WalkForwardEvidenceSummary(
        verdict=verdict,
        fold_count=fold_count,
        validated_fold_count=validated_fold_count,
        skipped_fold_count=skipped_fold_count,
        aggregate_test_metrics=dict(aggregate_test_metrics),
        aggregate_benchmark_metrics=dict(aggregate_benchmark_metrics),
        artifact_paths=dict(artifact_paths or {}),
        metadata=dict(metadata or {}),
    )


def _build_search_context(
    strategy_spec: StrategySpec,
    search_summary: SearchSummary | None,
) -> tuple[int | None, int | None, str | None, float | None]:
    if search_summary is None or search_summary.best_result is None:
        return None, None, None, None
    best_result = search_summary.best_result
    if best_result.strategy_spec.name != strategy_spec.name:
        return None, None, None, None
    if best_result.strategy_spec.parameters != strategy_spec.parameters:
        return None, None, None, None
    return 1, search_summary.result_count, search_summary.ranking_score, best_result.score


def _build_benchmark_relative_summary(
    test_result: ExperimentResult | None,
    benchmark_summary: dict[str, float] | None,
) -> dict[str, float]:
    normalized_benchmark = normalize_benchmark_summary(benchmark_summary)
    if test_result is None:
        return {
            "test_total_return": 0.0,
            "benchmark_total_return": normalized_benchmark.get("total_return", 0.0),
            "return_excess": 0.0 - normalized_benchmark.get("total_return", 0.0),
            "test_max_drawdown": 0.0,
            "benchmark_max_drawdown": normalized_benchmark.get("max_drawdown", 0.0),
            "max_drawdown_gap": 0.0 - normalized_benchmark.get("max_drawdown", 0.0),
        }
    return {
        "test_total_return": test_result.metrics.total_return,
        "benchmark_total_return": normalized_benchmark.get("total_return", 0.0),
        "return_excess": test_result.metrics.total_return - normalized_benchmark.get("total_return", 0.0),
        "test_max_drawdown": test_result.metrics.max_drawdown,
        "benchmark_max_drawdown": normalized_benchmark.get("max_drawdown", 0.0),
        "max_drawdown_gap": test_result.metrics.max_drawdown - normalized_benchmark.get("max_drawdown", 0.0),
    }


def _build_degradation_summary(
    train_metrics: MetricReport | None,
    test_metrics: MetricReport | None,
) -> dict[str, float]:
    if train_metrics is None or test_metrics is None:
        return {}
    return {
        "return_degradation": test_metrics.total_return - train_metrics.total_return,
        "sharpe_degradation": test_metrics.sharpe_ratio - train_metrics.sharpe_ratio,
        "max_drawdown_delta": test_metrics.max_drawdown - train_metrics.max_drawdown,
    }
