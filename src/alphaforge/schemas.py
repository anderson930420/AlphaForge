from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from .policy_types import CandidateVerdict, ParameterGrid, ResearchPolicyVerdict

# AlphaForge intentionally uses pandas.DataFrame as the shared in-memory
# equity-curve interface. Runtime-owned column contracts live in backtest.py.
EquityCurveFrame = pd.DataFrame
PermutationTargetMetricName = Literal["score", "sharpe_ratio"]


@dataclass(frozen=True)
class DataSpec:
    path: Path
    symbol: str = "UNKNOWN"
    datetime_column: str = "datetime"


@dataclass(frozen=True)
class StrategySpec:
    name: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float
    fee_rate: float
    slippage_rate: float
    annualization_factor: int = 252


@dataclass(frozen=True)
class TradeRecord:
    entry_time: str
    exit_time: str
    side: str
    quantity: float
    entry_price: float
    exit_price: float
    gross_return: float
    net_pnl: float


@dataclass(frozen=True)
class MetricReport:
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    turnover: float
    trade_count: int
    bar_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.bar_count, int):
            raise TypeError(f"MetricReport.bar_count must be an integer, got {type(self.bar_count).__name__}")
        if self.bar_count <= 0:
            raise ValueError(f"MetricReport.bar_count must be positive, got {self.bar_count}")


@dataclass(frozen=True)
class ExperimentResult:
    data_spec: DataSpec
    strategy_spec: StrategySpec
    backtest_config: BacktestConfig
    metrics: MetricReport
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


PolicyScope = Literal["validate-search", "walk-forward"]
ValidationPermutationStatus = Literal["skipped", "completed_passed", "completed_failed", "error"]


@dataclass(frozen=True)
class CandidatePolicyDecision:
    policy_name: str
    policy_scope: PolicyScope
    verdict: CandidateVerdict
    decision_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SearchSummary:
    strategy_name: str
    search_parameter_names: list[str]
    attempted_combinations: int
    valid_combinations: int
    invalid_combinations: int
    result_count: int
    ranking_score: str
    best_result: ExperimentResult | None = None
    top_results: list[ExperimentResult] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateEvidenceSummary:
    strategy_name: str
    strategy_parameters: dict[str, Any]
    verdict: CandidateVerdict
    search_rank: int | None = None
    search_result_count: int | None = None
    search_ranking_score: str | None = None
    search_score: float | None = None
    train_metrics: MetricReport | None = None
    test_metrics: MetricReport | None = None
    permutation_summary: PermutationTestSummary | None = None
    permutation_status: ValidationPermutationStatus = "skipped"
    benchmark_relative_summary: dict[str, float] = field(default_factory=dict)
    degradation_summary: dict[str, float] = field(default_factory=dict)
    artifact_paths: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WalkForwardEvidenceSummary:
    verdict: CandidateVerdict
    fold_count: int
    validated_fold_count: int
    skipped_fold_count: int
    aggregate_test_metrics: dict[str, float | int] = field(default_factory=dict)
    aggregate_benchmark_metrics: dict[str, float | int] = field(default_factory=dict)
    artifact_paths: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationSplitConfig:
    split_ratio: float


@dataclass(frozen=True)
class ValidationPermutationConfig:
    enabled: bool = False
    permutations: int = 25
    seed: int = 42
    block_size: int = 2
    null_model: str = "return_block_reconstruction"
    scope: str = "test"
    target_metric_name: PermutationTargetMetricName = "score"


@dataclass(frozen=True)
class ValidationResult:
    data_spec: DataSpec
    split_config: ValidationSplitConfig
    selected_strategy_spec: StrategySpec
    train_best_result: ExperimentResult
    test_result: ExperimentResult
    test_benchmark_summary: dict[str, float] = field(default_factory=dict)
    permutation_config: ValidationPermutationConfig | None = None
    candidate_evidence: CandidateEvidenceSummary | None = None
    candidate_decision: CandidatePolicyDecision | None = None
    research_policy_decision: Any | None = None
    research_policy_config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyFamilySearchConfig:
    strategy_name: str
    parameter_grid: ParameterGrid


@dataclass(frozen=True)
class StrategyComparisonConfig:
    data_spec: DataSpec
    split_config: ValidationSplitConfig
    backtest_config: BacktestConfig
    strategy_families: list[StrategyFamilySearchConfig]
    permutation_config: ValidationPermutationConfig | None = None
    research_policy_config: Any | None = None
    max_drawdown_cap: float | None = None
    min_trade_count: int | None = None
    holdout_cutoff_date: str | None = None
    output_dir: Path | None = None
    experiment_name: str = "alphaforge_run"


@dataclass(frozen=True)
class StrategyComparisonResult:
    strategy_name: str
    selected_strategy_spec: StrategySpec
    validation_result: ValidationResult
    train_score: float
    test_score: float
    permutation_status: ValidationPermutationStatus
    research_policy_verdict: ResearchPolicyVerdict | None = None
    candidate_policy_verdict: CandidateVerdict | None = None
    artifact_paths: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyComparisonSummary:
    data_spec: DataSpec
    split_config: ValidationSplitConfig
    backtest_config: BacktestConfig
    strategy_families: list[StrategyFamilySearchConfig]
    permutation_config: ValidationPermutationConfig | None
    research_policy_config: dict[str, Any]
    comparison_results: list[StrategyComparisonResult]
    artifact_paths: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WalkForwardConfig:
    train_size: int
    test_size: int
    step_size: int


@dataclass(frozen=True)
class WalkForwardFoldResult:
    fold_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    selected_strategy_spec: StrategySpec
    train_best_result: ExperimentResult
    test_result: ExperimentResult
    test_benchmark_summary: dict[str, float] = field(default_factory=dict)
    candidate_evidence: CandidateEvidenceSummary | None = None
    candidate_decision: CandidatePolicyDecision | None = None


@dataclass(frozen=True)
class WalkForwardResult:
    data_spec: DataSpec
    walk_forward_config: WalkForwardConfig
    folds: list[WalkForwardFoldResult]
    aggregate_test_metrics: dict[str, float | int]
    aggregate_benchmark_metrics: dict[str, float | int] = field(default_factory=dict)
    walk_forward_evidence: WalkForwardEvidenceSummary | None = None
    walk_forward_decision: CandidatePolicyDecision | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PermutationTestSummary:
    strategy_name: str
    strategy_parameters: dict[str, Any]
    target_metric_name: PermutationTargetMetricName
    permutation_mode: Literal["block"]
    block_size: int
    real_observed_metric_value: float
    permutation_metric_values: list[float]
    permutation_count: int
    seed: int
    null_ge_count: int
    empirical_p_value: float | None
    null_model: str = "return_block_reconstruction"
    artifact_paths: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PermutationTestArtifactReceipt:
    permutation_test_summary_path: Path
    permutation_scores_path: Path


@dataclass(frozen=True)
class PermutationTestExecutionOutput:
    permutation_test_summary: PermutationTestSummary
    artifact_receipt: PermutationTestArtifactReceipt | None = None


@dataclass(frozen=True)
class ResearchPeriod:
    start: str
    end: str


@dataclass(frozen=True)
class ResearchProtocolPlan:
    strategy_family: str
    selected_parameters: dict[str, Any]
    parameter_selection_rule: str
    scoring_formula_name: str
    transaction_cost_assumptions: dict[str, Any]
    development_period: ResearchPeriod
    holdout_period: ResearchPeriod
    search_space_size: int
    tried_strategy_family_count: int
    tried_parameter_combination_count: int
    walk_forward_config: WalkForwardConfig
    permutation_config: ValidationPermutationConfig | None = None


@dataclass(frozen=True)
class ResearchValidationConfig:
    data_spec: DataSpec
    strategy_name: str
    parameter_grid: ParameterGrid
    development_period: ResearchPeriod
    holdout_period: ResearchPeriod
    walk_forward_config: WalkForwardConfig
    backtest_config: BacktestConfig
    permutation_config: ValidationPermutationConfig | None = None
    max_drawdown_cap: float | None = None
    min_trade_count: int | None = None
    output_dir: Path | None = None
    experiment_name: str = "research_validation"


@dataclass(frozen=True)
class ResearchProtocolSummary:
    data_spec: DataSpec
    backtest_config: BacktestConfig
    development_period: ResearchPeriod
    holdout_period: ResearchPeriod
    development_row_count: int
    holdout_row_count: int
    selected_strategy: str
    selected_parameters: dict[str, Any]
    selection_rule: str
    scoring_formula_name: str
    development_search_data_window: dict[str, Any]
    walk_forward_data_window: dict[str, Any]
    final_holdout_data_window: dict[str, Any]
    search_space_size: int
    tried_strategy_family_count: int
    tried_parameter_combination_count: int
    development_search_summary: SearchSummary
    walk_forward_summary: WalkForwardResult
    frozen_plan: ResearchProtocolPlan
    final_holdout_result: ExperimentResult
    transaction_cost_assumptions: dict[str, Any]
    permutation_summary: PermutationTestSummary | None = None
    artifact_paths: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
