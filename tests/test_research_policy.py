from __future__ import annotations

from alphaforge.research_policy import ResearchPolicyConfig, evaluate_candidate_policy
from alphaforge.schemas import CandidateEvidenceSummary, MetricReport, PermutationTestSummary


def _make_evidence(
    *,
    trade_count: int = 4,
    max_drawdown: float = -0.08,
    return_degradation: float = 0.02,
) -> CandidateEvidenceSummary:
    return CandidateEvidenceSummary(
        strategy_name="ma_crossover",
        strategy_parameters={"short_window": 2, "long_window": 4},
        verdict="validated",
        test_metrics=MetricReport(
            total_return=0.12,
            annualized_return=0.15,
            sharpe_ratio=1.1,
            max_drawdown=max_drawdown,
            win_rate=0.6,
            turnover=1.0,
            trade_count=trade_count, bar_count=1),
        degradation_summary={
            "return_degradation": return_degradation,
            "sharpe_degradation": 0.1,
            "max_drawdown_delta": 0.02,
        },
    )


def _make_permutation_summary(
    *,
    empirical_p_value: float | None = 0.04,
    null_model: str = "return_block_reconstruction",
    permutation_scope: str = "candidate_fixed",
) -> PermutationTestSummary:
    return PermutationTestSummary(
        strategy_name="ma_crossover",
        strategy_parameters={"short_window": 2, "long_window": 4},
        target_metric_name="score",
        permutation_mode="block",
        block_size=2,
        real_observed_metric_value=0.3,
        permutation_metric_values=[0.1, 0.2],
        permutation_count=2,
        seed=11,
        null_ge_count=0,
        empirical_p_value=empirical_p_value,
        null_model=null_model,
        metadata={"permutation_scope": permutation_scope},
    )


def test_research_policy_promotes_when_all_configured_checks_pass() -> None:
    decision = evaluate_candidate_policy(
        _make_evidence(),
        permutation_summary=_make_permutation_summary(empirical_p_value=0.05),
        config=ResearchPolicyConfig(required_permutation_scope="candidate_fixed"),
        candidate_id="candidate-1",
    )

    assert decision.candidate_id == "candidate-1"
    assert decision.verdict == "promote"
    assert all(decision.checks.values())
    assert "all configured research policy checks passed" in decision.reasons


def test_research_policy_rejects_when_default_p_value_threshold_is_exceeded() -> None:
    decision = evaluate_candidate_policy(
        _make_evidence(),
        permutation_summary=_make_permutation_summary(empirical_p_value=0.2),
        config=ResearchPolicyConfig(required_permutation_scope="candidate_fixed"),
    )

    assert decision.verdict == "reject"
    assert decision.checks["max_permutation_p_value"] is False
    assert any("permutation p-value 0.2 above maximum 0.05" == reason for reason in decision.reasons)


def test_research_policy_rejects_when_trade_count_is_below_threshold() -> None:
    decision = evaluate_candidate_policy(
        _make_evidence(trade_count=1),
        permutation_summary=_make_permutation_summary(),
        config=ResearchPolicyConfig(min_trade_count=2),
    )

    assert decision.verdict == "reject"
    assert decision.checks["min_trade_count"] is False
    assert any("trade_count 1 below minimum 2" == reason for reason in decision.reasons)


def test_research_policy_rejects_when_return_degradation_is_below_threshold() -> None:
    decision = evaluate_candidate_policy(
        _make_evidence(return_degradation=-0.01),
        permutation_summary=_make_permutation_summary(),
        config=ResearchPolicyConfig(min_return_degradation=0.0),
    )

    assert decision.verdict == "reject"
    assert decision.checks["min_return_degradation"] is False
    assert any("return_degradation -0.01 below minimum 0.0" == reason for reason in decision.reasons)


def test_research_policy_rejects_when_permutation_p_value_exceeds_threshold() -> None:
    decision = evaluate_candidate_policy(
        _make_evidence(),
        permutation_summary=_make_permutation_summary(empirical_p_value=0.2),
        config=ResearchPolicyConfig(max_permutation_p_value=0.05),
    )

    assert decision.verdict == "reject"
    assert decision.checks["max_permutation_p_value"] is False
    assert any("permutation p-value 0.2 above maximum 0.05" == reason for reason in decision.reasons)


def test_research_policy_rejects_when_permutation_p_value_is_missing() -> None:
    decision = evaluate_candidate_policy(
        _make_evidence(),
        permutation_summary=_make_permutation_summary(empirical_p_value=None),
        config=ResearchPolicyConfig(required_permutation_null_model="return_block_reconstruction"),
    )

    assert decision.verdict == "reject"
    assert decision.checks["max_permutation_p_value"] is False
    assert any("missing permutation p-value" == reason for reason in decision.reasons)


def test_research_policy_skips_p_value_enforcement_when_explicitly_disabled() -> None:
    decision = evaluate_candidate_policy(
        _make_evidence(),
        permutation_summary=_make_permutation_summary(empirical_p_value=0.2),
        config=ResearchPolicyConfig(max_permutation_p_value=None, required_permutation_scope="candidate_fixed"),
    )

    assert decision.verdict == "promote"
    assert "max_permutation_p_value" not in decision.checks


def test_research_policy_rejects_when_required_null_model_mismatches() -> None:
    decision = evaluate_candidate_policy(
        _make_evidence(),
        permutation_summary=_make_permutation_summary(null_model="legacy_absolute_block_shuffle"),
        config=ResearchPolicyConfig(required_permutation_null_model="return_block_reconstruction"),
    )

    assert decision.verdict == "reject"
    assert decision.checks["required_permutation_null_model"] is False
    assert any("does not match required return_block_reconstruction" in reason for reason in decision.reasons)


def test_research_policy_blocks_when_rerun_count_exceeds_max_reruns() -> None:
    decision = evaluate_candidate_policy(
        _make_evidence(),
        permutation_summary=_make_permutation_summary(),
        config=ResearchPolicyConfig(max_reruns=1),
        rerun_count=2,
    )

    assert decision.verdict == "blocked"
    assert decision.max_reruns == 1
    assert decision.rerun_count == 2
    assert decision.checks == {"rerun_count_within_limit": False}
    assert decision.reasons == ["rerun_count 2 exceeds max_reruns 1"]


def test_research_policy_decision_includes_human_readable_reasons_and_check_results() -> None:
    decision = evaluate_candidate_policy(
        _make_evidence(),
        permutation_summary=_make_permutation_summary(),
        config=ResearchPolicyConfig(max_drawdown_cap=0.1, max_permutation_p_value=0.05),
    )

    assert decision.verdict == "promote"
    assert decision.reasons
    assert all(isinstance(reason, str) and reason for reason in decision.reasons)
    assert decision.checks["max_drawdown_cap"] is True
    assert decision.checks["max_permutation_p_value"] is True


def test_research_policy_consumes_default_candidate_fixed_permutation_scope_when_metadata_is_absent() -> None:
    summary = _make_permutation_summary()
    summary.metadata.clear()

    decision = evaluate_candidate_policy(
        _make_evidence(),
        permutation_summary=summary,
        config=ResearchPolicyConfig(required_permutation_scope="candidate_fixed"),
    )

    assert decision.verdict == "promote"
    assert decision.checks["required_permutation_scope"] is True
