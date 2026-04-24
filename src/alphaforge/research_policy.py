from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .schemas import CandidateEvidenceSummary, PermutationTestSummary

ResearchPolicyVerdict = Literal["promote", "reject", "blocked"]
DEFAULT_PERMUTATION_SCOPE = "candidate_fixed"


@dataclass(frozen=True)
class ResearchPolicyConfig:
    max_reruns: int = 0
    min_trade_count: int = 1
    max_drawdown_cap: float | None = None
    min_return_degradation: float = 0.0
    max_permutation_p_value: float | None = 0.05
    required_permutation_null_model: str | None = "return_block_reconstruction"
    required_permutation_scope: str | None = None


@dataclass(frozen=True)
class PolicyDecision:
    candidate_id: str | None
    verdict: ResearchPolicyVerdict
    reasons: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)
    max_reruns: int = 0
    rerun_count: int = 0


def evaluate_candidate_policy(
    candidate_evidence: CandidateEvidenceSummary,
    *,
    permutation_summary: PermutationTestSummary | None = None,
    config: ResearchPolicyConfig | None = None,
    candidate_id: str | None = None,
    rerun_count: int = 0,
) -> PolicyDecision:
    """Evaluate already-computed evidence against research guardrails."""
    config = config or ResearchPolicyConfig()
    checks: dict[str, bool] = {}
    reasons: list[str] = []

    checks["rerun_count_within_limit"] = rerun_count <= config.max_reruns
    if not checks["rerun_count_within_limit"]:
        reasons.append(f"rerun_count {rerun_count} exceeds max_reruns {config.max_reruns}")
        return PolicyDecision(
            candidate_id=candidate_id,
            verdict="blocked",
            reasons=reasons,
            checks=checks,
            max_reruns=config.max_reruns,
            rerun_count=rerun_count,
        )
    reasons.append("rerun_count_within_limit")

    test_metrics = candidate_evidence.test_metrics
    checks["test_metrics_present"] = test_metrics is not None
    if test_metrics is None:
        reasons.append("missing test metrics")
        return _decision(
            candidate_id=candidate_id,
            verdict="reject",
            reasons=reasons,
            checks=checks,
            config=config,
            rerun_count=rerun_count,
        )
    reasons.append("test_metrics_present")

    checks["min_trade_count"] = int(test_metrics.trade_count) >= config.min_trade_count
    if checks["min_trade_count"]:
        reasons.append(f"trade_count {test_metrics.trade_count} meets minimum {config.min_trade_count}")
    else:
        reasons.append(f"trade_count {test_metrics.trade_count} below minimum {config.min_trade_count}")

    if config.max_drawdown_cap is not None:
        drawdown_floor = -abs(config.max_drawdown_cap)
        checks["max_drawdown_cap"] = float(test_metrics.max_drawdown) >= drawdown_floor
        if checks["max_drawdown_cap"]:
            reasons.append(f"max_drawdown {test_metrics.max_drawdown} within cap {config.max_drawdown_cap}")
        else:
            reasons.append(f"max_drawdown {test_metrics.max_drawdown} exceeds cap {config.max_drawdown_cap}")

    return_degradation = candidate_evidence.degradation_summary.get("return_degradation")
    checks["return_degradation_present"] = return_degradation is not None
    if return_degradation is None:
        reasons.append("missing return_degradation")
    else:
        checks["min_return_degradation"] = float(return_degradation) >= config.min_return_degradation
        if checks["min_return_degradation"]:
            reasons.append(f"return_degradation {return_degradation} meets minimum {config.min_return_degradation}")
        else:
            reasons.append(f"return_degradation {return_degradation} below minimum {config.min_return_degradation}")

    if config.max_permutation_p_value is not None:
        checks["permutation_summary_present_for_p_value"] = permutation_summary is not None
        if permutation_summary is None:
            reasons.append("missing permutation summary for p-value check")
        else:
            empirical_p_value = permutation_summary.empirical_p_value
            checks["max_permutation_p_value"] = empirical_p_value is not None and float(empirical_p_value) <= config.max_permutation_p_value
            if empirical_p_value is None:
                reasons.append("missing permutation p-value")
            elif checks["max_permutation_p_value"]:
                reasons.append(
                    f"permutation p-value {empirical_p_value} within maximum {config.max_permutation_p_value}"
                )
            else:
                reasons.append(
                    f"permutation p-value {empirical_p_value} above maximum {config.max_permutation_p_value}"
                )

    if config.required_permutation_null_model is not None:
        checks["permutation_summary_present_for_null_model"] = permutation_summary is not None
        if permutation_summary is None:
            reasons.append("missing permutation summary for null-model check")
        else:
            checks["required_permutation_null_model"] = (
                permutation_summary.null_model == config.required_permutation_null_model
            )
            if checks["required_permutation_null_model"]:
                reasons.append(f"permutation null_model {permutation_summary.null_model} matches requirement")
            else:
                reasons.append(
                    f"permutation null_model {permutation_summary.null_model} does not match required {config.required_permutation_null_model}"
                )

    if config.required_permutation_scope is not None:
        checks["permutation_summary_present_for_scope"] = permutation_summary is not None
        if permutation_summary is None:
            reasons.append("missing permutation summary for scope check")
        else:
            permutation_scope = str(permutation_summary.metadata.get("permutation_scope", DEFAULT_PERMUTATION_SCOPE))
            checks["required_permutation_scope"] = permutation_scope == config.required_permutation_scope
            if checks["required_permutation_scope"]:
                reasons.append(f"permutation_scope {permutation_scope} matches requirement")
            else:
                reasons.append(
                    f"permutation_scope {permutation_scope} does not match required {config.required_permutation_scope}"
                )

    verdict: ResearchPolicyVerdict = "promote" if all(checks.values()) else "reject"
    if verdict == "promote":
        reasons.append("all configured research policy checks passed")
    return _decision(
        candidate_id=candidate_id,
        verdict=verdict,
        reasons=reasons,
        checks=checks,
        config=config,
        rerun_count=rerun_count,
    )


def _decision(
    *,
    candidate_id: str | None,
    verdict: ResearchPolicyVerdict,
    reasons: list[str],
    checks: dict[str, bool],
    config: ResearchPolicyConfig,
    rerun_count: int,
) -> PolicyDecision:
    return PolicyDecision(
        candidate_id=candidate_id,
        verdict=verdict,
        reasons=reasons,
        checks=checks,
        max_reruns=config.max_reruns,
        rerun_count=rerun_count,
    )
