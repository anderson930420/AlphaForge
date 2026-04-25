from __future__ import annotations

from typing import get_args, get_type_hints

from alphaforge.policy_types import CandidateVerdict, ParameterGrid, ResearchPolicyVerdict
from alphaforge.schemas import StrategyComparisonResult, StrategyFamilySearchConfig


def test_strategy_comparison_verdict_domains_are_distinct() -> None:
    hints = get_type_hints(StrategyComparisonResult)

    assert hints["research_policy_verdict"] == ResearchPolicyVerdict | None
    assert hints["candidate_policy_verdict"] == CandidateVerdict | None
    assert set(get_args(ResearchPolicyVerdict)) == {"promote", "reject", "blocked"}
    assert set(get_args(CandidateVerdict)) == {"candidate", "validated", "rejected", "inconclusive"}
    assert set(get_args(ResearchPolicyVerdict)).isdisjoint(set(get_args(CandidateVerdict)))


def test_strategy_family_parameter_grid_accepts_numeric_float_contract() -> None:
    hints = get_type_hints(StrategyFamilySearchConfig)
    config = StrategyFamilySearchConfig(
        strategy_name="future_numeric_threshold_strategy",
        parameter_grid={
            "threshold": [0.1, 0.25],
            "window": [2],
        },
    )

    assert hints["parameter_grid"] == ParameterGrid
    assert config.parameter_grid["threshold"] == [0.1, 0.25]
    assert config.parameter_grid["window"] == [2]
