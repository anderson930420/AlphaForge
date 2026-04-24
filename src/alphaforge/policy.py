from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .schemas import (
    CandidateEvidenceSummary,
    CandidatePolicyDecision,
    CandidateVerdict,
    PolicyScope,
    WalkForwardEvidenceSummary,
)

POLICY_NAME = "post_search_candidate_policy"


def evaluate_candidate_policy(
    candidate_evidence: CandidateEvidenceSummary,
    *,
    policy_scope: PolicyScope,
) -> CandidatePolicyDecision:
    train_metrics = candidate_evidence.train_metrics
    test_metrics = candidate_evidence.test_metrics
    if train_metrics is None:
        return _decision(policy_scope=policy_scope, verdict="inconclusive", reasons=["missing_train_metrics"])
    if test_metrics is None:
        return _decision(policy_scope=policy_scope, verdict="inconclusive", reasons=["missing_test_metrics"])

    degradation_summary = candidate_evidence.degradation_summary
    benchmark_relative_summary = candidate_evidence.benchmark_relative_summary
    if not _has_required_keys(
        degradation_summary,
        ("return_degradation", "sharpe_degradation", "max_drawdown_delta"),
    ):
        return _decision(policy_scope=policy_scope, verdict="inconclusive", reasons=["missing_degradation_summary"])
    if not _has_required_keys(
        benchmark_relative_summary,
        ("return_excess",),
    ):
        return _decision(policy_scope=policy_scope, verdict="inconclusive", reasons=["missing_benchmark_relative_summary"])

    test_total_return = float(test_metrics.total_return)
    test_sharpe_ratio = float(test_metrics.sharpe_ratio)
    return_degradation = float(degradation_summary["return_degradation"])
    sharpe_degradation = float(degradation_summary["sharpe_degradation"])
    max_drawdown_delta = float(degradation_summary["max_drawdown_delta"])
    return_excess = float(benchmark_relative_summary["return_excess"])

    if _validation_passes(
        test_total_return=test_total_return,
        test_sharpe_ratio=test_sharpe_ratio,
        return_degradation=return_degradation,
        sharpe_degradation=sharpe_degradation,
        max_drawdown_delta=max_drawdown_delta,
        return_excess=return_excess,
    ):
        return _decision(
            policy_scope=policy_scope,
            verdict="validated",
            reasons=[
                "evidence_complete",
                "out_of_sample_return_positive",
                "out_of_sample_sharpe_positive",
                "return_degradation_non_negative",
                "sharpe_degradation_non_negative",
                "max_drawdown_delta_non_negative",
                "benchmark_return_excess_non_negative",
            ],
        )

    if test_total_return <= 0.0:
        return _decision(
            policy_scope=policy_scope,
            verdict="rejected",
            reasons=[
                "evidence_complete",
                "out_of_sample_return_non_positive",
            ],
        )

    if test_sharpe_ratio <= 0.0:
        return _decision(
            policy_scope=policy_scope,
            verdict="rejected",
            reasons=[
                "evidence_complete",
                "out_of_sample_sharpe_non_positive",
            ],
        )

    if return_degradation < 0.0 and sharpe_degradation < 0.0 and max_drawdown_delta < 0.0:
        return _decision(
            policy_scope=policy_scope,
            verdict="rejected",
            reasons=[
                "evidence_complete",
                "all_degradation_signals_negative",
            ],
        )

    return _decision(
        policy_scope=policy_scope,
        verdict="inconclusive",
        reasons=[
            "evidence_complete",
            "mixed_signals",
        ],
    )


def evaluate_walk_forward_policy(
    walk_forward_evidence: WalkForwardEvidenceSummary,
) -> CandidatePolicyDecision:
    fold_count = int(walk_forward_evidence.fold_count)
    validated_fold_count = int(walk_forward_evidence.validated_fold_count)
    skipped_fold_count = int(walk_forward_evidence.skipped_fold_count)
    if fold_count <= 0:
        return _decision(
            policy_scope="walk-forward",
            verdict="inconclusive",
            reasons=["no_valid_folds"],
        )
    if validated_fold_count <= 0 or skipped_fold_count > 0 or validated_fold_count != fold_count:
        return _decision(
            policy_scope="walk-forward",
            verdict="inconclusive",
            reasons=[
                "fold_coverage_incomplete",
            ],
        )

    aggregate_test_metrics = walk_forward_evidence.aggregate_test_metrics
    aggregate_benchmark_metrics = walk_forward_evidence.aggregate_benchmark_metrics
    if not _has_required_keys(
        aggregate_test_metrics,
        ("mean_test_total_return", "mean_test_sharpe_ratio", "mean_test_max_drawdown"),
    ):
        return _decision(
            policy_scope="walk-forward",
            verdict="inconclusive",
            reasons=["missing_aggregate_test_metrics"],
        )
    if not _has_required_keys(
        aggregate_benchmark_metrics,
        ("mean_benchmark_max_drawdown", "mean_excess_return"),
    ):
        return _decision(
            policy_scope="walk-forward",
            verdict="inconclusive",
            reasons=["missing_aggregate_benchmark_metrics"],
        )

    mean_test_total_return = float(aggregate_test_metrics["mean_test_total_return"])
    mean_test_max_drawdown = float(aggregate_test_metrics["mean_test_max_drawdown"])
    mean_benchmark_max_drawdown = float(aggregate_benchmark_metrics["mean_benchmark_max_drawdown"])
    mean_excess_return = float(aggregate_benchmark_metrics["mean_excess_return"])
    pooled_test_sharpe_ratio = aggregate_test_metrics.get("pooled_test_sharpe_ratio")
    if pooled_test_sharpe_ratio is None:
        return _decision(
            policy_scope="walk-forward",
            verdict="inconclusive",
            reasons=[
                "fold_coverage_complete",
                "missing_pooled_test_sharpe_ratio",
            ],
        )

    if _walk_forward_passes(
        mean_test_total_return=mean_test_total_return,
        pooled_test_sharpe_ratio=float(pooled_test_sharpe_ratio),
        mean_test_max_drawdown=mean_test_max_drawdown,
        mean_benchmark_max_drawdown=mean_benchmark_max_drawdown,
        mean_excess_return=mean_excess_return,
    ):
        return _decision(
            policy_scope="walk-forward",
            verdict="validated",
            reasons=[
                "fold_coverage_complete",
                "aggregate_return_positive",
                "aggregate_pooled_sharpe_positive",
                "aggregate_return_excess_non_negative",
                "aggregate_drawdown_non_worsening",
            ],
        )

    if mean_test_total_return <= 0.0:
        return _decision(
            policy_scope="walk-forward",
            verdict="rejected",
            reasons=[
                "fold_coverage_complete",
                "aggregate_return_non_positive",
            ],
        )

    if float(pooled_test_sharpe_ratio) <= 0.0:
        return _decision(
            policy_scope="walk-forward",
            verdict="rejected",
            reasons=[
                "fold_coverage_complete",
                "aggregate_pooled_sharpe_non_positive",
            ],
        )

    if mean_excess_return < 0.0 and mean_test_max_drawdown < mean_benchmark_max_drawdown:
        return _decision(
            policy_scope="walk-forward",
            verdict="rejected",
            reasons=[
                "fold_coverage_complete",
                "aggregate_relative_performance_negative",
            ],
        )

    return _decision(
        policy_scope="walk-forward",
        verdict="inconclusive",
        reasons=[
            "fold_coverage_complete",
            "mixed_signals",
        ],
    )


def apply_policy_decision(
    evidence: CandidateEvidenceSummary | WalkForwardEvidenceSummary,
    decision: CandidatePolicyDecision,
) -> CandidateEvidenceSummary | WalkForwardEvidenceSummary:
    return replace(evidence, verdict=decision.verdict)


def _validation_passes(
    *,
    test_total_return: float,
    test_sharpe_ratio: float,
    return_degradation: float,
    sharpe_degradation: float,
    max_drawdown_delta: float,
    return_excess: float,
) -> bool:
    return (
        test_total_return > 0.0
        and test_sharpe_ratio > 0.0
        and return_degradation >= 0.0
        and sharpe_degradation >= 0.0
        and max_drawdown_delta >= 0.0
        and return_excess >= 0.0
    )


def _walk_forward_passes(
    *,
    mean_test_total_return: float,
    pooled_test_sharpe_ratio: float,
    mean_test_max_drawdown: float,
    mean_benchmark_max_drawdown: float,
    mean_excess_return: float,
) -> bool:
    return (
        mean_test_total_return > 0.0
        and pooled_test_sharpe_ratio > 0.0
        and mean_excess_return >= 0.0
        and mean_test_max_drawdown >= mean_benchmark_max_drawdown
    )


def _decision(
    *,
    policy_scope: PolicyScope,
    verdict: CandidateVerdict,
    reasons: list[str],
) -> CandidatePolicyDecision:
    return CandidatePolicyDecision(
        policy_name=POLICY_NAME,
        policy_scope=policy_scope,
        verdict=verdict,
        decision_reasons=reasons,
    )


def _has_required_keys(payload: dict[str, float | int], required_keys: Iterable[str]) -> bool:
    return all(key in payload for key in required_keys)
