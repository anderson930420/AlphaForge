from __future__ import annotations

"""Workflow-specific runner orchestration implementations.

This module owns the concrete sequencing for single-run, search,
validate-search, and walk-forward workflows. It consumes canonical runtime,
evidence, persistence, and presentation owners without redefining them.
"""

from dataclasses import replace
from pathlib import Path

import pandas as pd

from .backtest import run_backtest
from .benchmark import build_buy_and_hold_equity_curve, normalize_benchmark_summary, summarize_buy_and_hold
from .data_loader import load_market_data, split_holdout_data
from .evidence import build_candidate_evidence_summary, build_walk_forward_evidence_summary
from .experiment_runner import (
    ExperimentExecutionOutput,
    SearchExecutionOutput,
    StrategyComparisonExecutionOutput,
    ValidationExecutionOutput,
    WalkForwardExecutionOutput,
)
from .metrics import compute_metrics
from .permutation import run_permutation_test_with_details
from .policy_types import ParameterGrid
from .policy import apply_policy_decision, evaluate_candidate_policy, evaluate_walk_forward_policy
from .report import build_experiment_report_input
from .research_policy import ResearchPolicyConfig, evaluate_candidate_policy as evaluate_research_policy
from .runner_protocols import (
    build_execution_metadata,
    build_holdout_metadata,
    build_strategy,
    build_validation_metadata,
    generate_walk_forward_folds,
    resolve_backtest_config,
    split_market_data_by_ratio,
    validate_train_windows,
    workflow_root,
)
from .schemas import (
    BacktestConfig,
    DataSpec,
    ExperimentResult,
    SearchSummary,
    StrategySpec,
    StrategyComparisonConfig,
    StrategyComparisonResult,
    StrategyComparisonSummary,
    ValidationResult,
    ValidationSplitConfig,
    PermutationTestArtifactReceipt,
    PermutationTestSummary,
    WalkForwardConfig,
    WalkForwardFoldResult,
    WalkForwardResult,
    ValidationPermutationConfig,
    ValidationPermutationStatus,
)
from .scoring import RANKING_SCORE_FIELD, rank_results, score_metrics, select_best_result, select_top_results
from .search import SearchSpaceEvaluation, evaluate_strategy_search_space
from .search_reporting import save_best_search_report, save_search_comparison_report
from .storage import (
    ArtifactReceipt,
    FOLD_RESULTS_FILENAME,
    SearchArtifactReceipt,
    TRAIN_RANKED_RESULTS_FILENAME,
    VALIDATION_SUMMARY_FILENAME,
    ValidationArtifactReceipt,
    WALK_FORWARD_SUMMARY_FILENAME,
    WalkForwardArtifactReceipt,
    save_ranked_results_artifact,
    save_ranked_results_with_columns,
    save_single_experiment,
    save_strategy_comparison_summary,
    save_validation_result,
    save_walk_forward_result,
    serialize_validation_artifact_receipt,
)
from .strategy_registry import get_strategy_registration
from .walk_forward_aggregation import aggregate_walk_forward_benchmark_metrics, aggregate_walk_forward_test_metrics


def run_experiment_with_artifacts_workflow(
    data_spec: DataSpec,
    strategy_spec: StrategySpec,
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "single_experiment",
    holdout_cutoff_date: str | None = None,
) -> ExperimentExecutionOutput:
    backtest_config = resolve_backtest_config(backtest_config)
    market_data = load_market_data(data_spec)
    market_data = _apply_holdout_cutoff_if_requested(market_data, holdout_cutoff_date)
    return run_experiment_on_market_data(
        market_data=market_data,
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
    )


def run_experiment_on_market_data(
    market_data: pd.DataFrame,
    data_spec: DataSpec,
    strategy_spec: StrategySpec,
    backtest_config: BacktestConfig,
    output_dir: Path | None = None,
    experiment_name: str = "single_experiment",
) -> ExperimentExecutionOutput:
    receipt: ArtifactReceipt | None = None
    strategy = build_strategy(strategy_spec)
    target_positions = strategy.generate_signals(market_data)
    equity_curve, trades = run_backtest(market_data, target_positions, backtest_config)
    metrics = compute_metrics(equity_curve, trades, backtest_config.annualization_factor)
    benchmark_summary = summarize_buy_and_hold(market_data, backtest_config.initial_capital)
    result = ExperimentResult(
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        backtest_config=backtest_config,
        metrics=metrics,
        score=score_metrics(metrics),
        metadata=build_execution_metadata(market_data, benchmark_summary),
    )
    if output_dir is not None:
        result, receipt = save_single_experiment(output_dir, experiment_name, result, equity_curve, trades)
    report_input = build_experiment_report_input(
        result=result,
        equity_curve=equity_curve,
        trades=trades,
        benchmark_summary=benchmark_summary,
        benchmark_curve=build_buy_and_hold_equity_curve(equity_curve, backtest_config.initial_capital),
    )
    return ExperimentExecutionOutput(
        result=result,
        equity_curve=equity_curve,
        trade_log=trades,
        report_input=report_input,
        artifact_receipt=receipt,
    )


def run_search_with_details_workflow(
    data_spec: DataSpec,
    parameter_grid: ParameterGrid,
    strategy_name: str = "ma_crossover",
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "search_experiment",
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
    generate_best_report: bool = False,
    holdout_cutoff_date: str | None = None,
) -> SearchExecutionOutput:
    backtest_config = resolve_backtest_config(backtest_config)
    market_data = load_market_data(data_spec)
    market_data = _apply_holdout_cutoff_if_requested(market_data, holdout_cutoff_date)
    return run_search_on_market_data(
        market_data=market_data,
        data_spec=data_spec,
        parameter_grid=parameter_grid,
        strategy_name=strategy_name,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
        generate_best_report=generate_best_report,
    )


def run_search_on_market_data(
    market_data: pd.DataFrame,
    data_spec: DataSpec,
    parameter_grid: ParameterGrid,
    backtest_config: BacktestConfig,
    strategy_name: str = "ma_crossover",
    output_dir: Path | None = None,
    experiment_name: str = "search_experiment",
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
    generate_best_report: bool = False,
) -> SearchExecutionOutput:
    results: list[ExperimentResult] = []
    artifact_receipts_by_result_id: dict[int, ArtifactReceipt] = {}
    ranked_results_path: Path | None = None
    best_report_path: Path | None = None
    comparison_report_path: Path | None = None
    search_space = evaluate_strategy_search_space(strategy_name, parameter_grid)
    strategy_specs = list(search_space.strategy_specs)
    search_root = workflow_root(output_dir, experiment_name)
    runs_output_dir = (search_root / "runs") if search_root is not None else None
    for index, strategy_spec in enumerate(strategy_specs, start=1):
        execution = run_experiment_on_market_data(
            market_data=market_data,
            data_spec=data_spec,
            strategy_spec=strategy_spec,
            backtest_config=backtest_config,
            output_dir=runs_output_dir,
            experiment_name=f"run_{index:03d}",
        )
        results.append(execution.result)
        if execution.artifact_receipt is not None:
            artifact_receipts_by_result_id[id(execution.result)] = execution.artifact_receipt

    ranked = rank_results(
        results,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
    )
    summary = _build_search_summary(search_space, ranked)
    if output_dir is not None:
        parameter_columns = list(parameter_grid)
        ranked_results_path = save_ranked_results_with_columns(search_root, ranked, parameter_columns=parameter_columns)
        ranked_receipts = [artifact_receipts_by_result_id.get(id(result)) for result in ranked]
        if generate_best_report:
            best_receipt = artifact_receipts_by_result_id.get(id(summary.best_result)) if summary.best_result is not None else None
            best_report_path = (
                save_best_search_report(search_root=search_root, best_result=summary.best_result, artifact_receipt=best_receipt)
                if summary.best_result is not None
                else None
            )
            comparison_report_path = save_search_comparison_report(
                search_root=search_root,
                ranked_results=ranked,
                artifact_receipts=ranked_receipts,
                best_report_path=best_report_path,
            )
    search_artifact_receipt: SearchArtifactReceipt | None = None
    if output_dir is not None:
        search_artifact_receipt = SearchArtifactReceipt(
            search_root=search_root,
            ranked_results_path=ranked_results_path,
            best_report_path=best_report_path,
            comparison_report_path=comparison_report_path,
        )
    return SearchExecutionOutput(
        ranked_results=ranked,
        summary=summary,
        artifact_receipt=search_artifact_receipt,
    )


def run_validate_search_with_details_workflow(
    data_spec: DataSpec,
    parameter_grid: ParameterGrid,
    split_ratio: float,
    strategy_name: str = "ma_crossover",
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "validation_experiment",
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
    holdout_cutoff_date: str | None = None,
    policy_config: ResearchPolicyConfig | None = None,
    permutation_config: ValidationPermutationConfig | None = None,
) -> ValidationExecutionOutput:
    validation_result, validation_artifact_receipt = run_validate_search_on_market_data(
        data_spec=data_spec,
        parameter_grid=parameter_grid,
        split_ratio=split_ratio,
        strategy_name=strategy_name,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
        holdout_cutoff_date=holdout_cutoff_date,
        policy_config=policy_config,
        permutation_config=permutation_config,
    )
    return ValidationExecutionOutput(
        validation_result=validation_result,
        artifact_receipt=validation_artifact_receipt,
    )


def run_validate_search_on_market_data(
    data_spec: DataSpec,
    parameter_grid: ParameterGrid,
    split_ratio: float,
    strategy_name: str = "ma_crossover",
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "validation_experiment",
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
    holdout_cutoff_date: str | None = None,
    policy_config: ResearchPolicyConfig | None = None,
    permutation_config: ValidationPermutationConfig | None = None,
) -> tuple[ValidationResult, ValidationArtifactReceipt | None]:
    backtest_config = resolve_backtest_config(backtest_config)
    market_data = load_market_data(data_spec)
    market_data = _apply_holdout_cutoff_if_requested(market_data, holdout_cutoff_date)
    train_data, test_data = split_market_data_by_ratio(market_data, split_ratio)
    validate_train_windows(strategy_name, train_data, parameter_grid)

    validation_root = workflow_root(output_dir, experiment_name)
    search_execution = run_search_on_market_data(
        market_data=train_data,
        data_spec=data_spec,
        parameter_grid=parameter_grid,
        strategy_name=strategy_name,
        backtest_config=backtest_config,
        output_dir=None,
        experiment_name="train_search",
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
        generate_best_report=False,
    )
    ranked = search_execution.ranked_results
    if not ranked:
        raise ValueError("No train-segment results remain after ranking and threshold filters")

    best_ranked_result = select_best_result(ranked)
    assert best_ranked_result is not None
    selected_strategy_spec = best_ranked_result.strategy_spec
    train_best_result = best_ranked_result
    train_ranked_results_path = None
    train_best_receipt: ArtifactReceipt | None = None
    test_receipt: ArtifactReceipt | None = None
    if validation_root is not None:
        train_ranked_results_path = save_ranked_results_artifact(
            output_dir=validation_root,
            results=ranked,
            parameter_columns=list(parameter_grid),
            filename=TRAIN_RANKED_RESULTS_FILENAME,
        )
        train_best_execution = run_experiment_on_market_data(
            market_data=train_data,
            data_spec=data_spec,
            strategy_spec=selected_strategy_spec,
            backtest_config=backtest_config,
            output_dir=validation_root,
            experiment_name="train_best",
        )
        train_best_result = train_best_execution.result
        train_best_receipt = train_best_execution.artifact_receipt
    test_execution = run_experiment_on_market_data(
        market_data=test_data,
        data_spec=data_spec,
        strategy_spec=selected_strategy_spec,
        backtest_config=backtest_config,
        output_dir=validation_root,
        experiment_name="test_selected",
    )
    test_result = test_execution.result
    test_receipt = test_execution.artifact_receipt
    validation_permutation_config = permutation_config or ValidationPermutationConfig()
    permutation_summary = None
    permutation_artifact_receipt = None
    permutation_execution_error = False
    if validation_permutation_config.enabled:
        permutation_summary, permutation_artifact_receipt, permutation_execution_error = _run_validation_permutation_diagnostic(
            data_spec=data_spec,
            selected_strategy_spec=selected_strategy_spec,
            backtest_config=backtest_config,
            test_data=test_data,
            validation_root=validation_root,
            permutation_config=validation_permutation_config,
        )

    candidate_artifact_paths: dict[str, str] = {}
    if validation_root is not None:
        candidate_artifact_paths["validation_summary_path"] = str(validation_root / VALIDATION_SUMMARY_FILENAME)
        if train_ranked_results_path is not None:
            candidate_artifact_paths["train_ranked_results_path"] = str(train_ranked_results_path)
        if train_best_receipt is not None:
            candidate_artifact_paths["train_best_run_dir"] = str(train_best_receipt.run_dir)
            candidate_artifact_paths["train_best_equity_curve_path"] = str(train_best_receipt.equity_curve_path)
            candidate_artifact_paths["train_best_trade_log_path"] = str(train_best_receipt.trade_log_path)
            candidate_artifact_paths["train_best_metrics_summary_path"] = str(train_best_receipt.metrics_summary_path)
        if test_receipt is not None:
            candidate_artifact_paths["test_selected_run_dir"] = str(test_receipt.run_dir)
            candidate_artifact_paths["test_selected_equity_curve_path"] = str(test_receipt.equity_curve_path)
            candidate_artifact_paths["test_selected_trade_log_path"] = str(test_receipt.trade_log_path)
            candidate_artifact_paths["test_selected_metrics_summary_path"] = str(test_receipt.metrics_summary_path)
        if permutation_artifact_receipt is not None:
            candidate_artifact_paths["permutation_test_summary_path"] = str(permutation_artifact_receipt.permutation_test_summary_path)
            candidate_artifact_paths["permutation_scores_path"] = str(permutation_artifact_receipt.permutation_scores_path)

    research_policy_config = _resolve_research_policy_config(
        policy_config=policy_config,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
        permutation_config=validation_permutation_config,
    )
    permutation_status = _classify_validation_permutation_status(
        permutation_summary=permutation_summary,
        permutation_config=validation_permutation_config,
        research_policy_config=research_policy_config,
        execution_error=permutation_execution_error,
    )
    candidate_evidence = build_candidate_evidence_summary(
        strategy_spec=selected_strategy_spec,
        train_result=train_best_result,
        test_result=test_result,
        search_summary=search_execution.summary,
        benchmark_summary=normalize_benchmark_summary(test_result.metadata.get("benchmark_summary")),
        permutation_summary=permutation_summary,
        permutation_status=permutation_status,
        artifact_paths=candidate_artifact_paths,
        metadata=build_holdout_metadata(train_data),
    )
    research_policy_decision = evaluate_research_policy(
        candidate_evidence,
        permutation_summary=permutation_summary,
        config=research_policy_config,
        candidate_id=_build_research_policy_candidate_id(selected_strategy_spec, train_data, test_data),
    )
    candidate_decision = evaluate_candidate_policy(candidate_evidence, policy_scope="validate-search")
    candidate_evidence = apply_policy_decision(candidate_evidence, candidate_decision)
    validation_result = ValidationResult(
        data_spec=data_spec,
        split_config=ValidationSplitConfig(split_ratio=split_ratio),
        selected_strategy_spec=selected_strategy_spec,
        train_best_result=train_best_result,
        test_result=test_result,
        test_benchmark_summary=normalize_benchmark_summary(test_result.metadata.get("benchmark_summary")),
        permutation_config=validation_permutation_config,
        candidate_evidence=candidate_evidence,
        candidate_decision=candidate_decision,
        research_policy_decision=research_policy_decision,
        research_policy_config=_serialize_research_policy_config(research_policy_config),
        metadata=build_validation_metadata(train_data, test_data),
    )
    validation_artifact_receipt: ValidationArtifactReceipt | None = None
    if validation_root is not None:
        validation_result, validation_artifact_receipt = save_validation_result(
            validation_root,
            validation_result,
            train_ranked_results_path=train_ranked_results_path,
            permutation_artifact_receipt=permutation_artifact_receipt,
        )
    return validation_result, validation_artifact_receipt


def run_strategy_comparison_with_details_workflow(
    comparison_config: StrategyComparisonConfig,
) -> StrategyComparisonExecutionOutput:
    backtest_config = resolve_backtest_config(comparison_config.backtest_config)
    validation_permutation_config = comparison_config.permutation_config or ValidationPermutationConfig()
    _validate_strategy_comparison_families(comparison_config)

    comparison_root = workflow_root(comparison_config.output_dir, comparison_config.experiment_name)
    strategy_output_root = comparison_root / "strategies" if comparison_root is not None else None
    resolved_research_policy_config = _resolve_research_policy_config(
        policy_config=comparison_config.research_policy_config,
        max_drawdown_cap=comparison_config.max_drawdown_cap,
        min_trade_count=comparison_config.min_trade_count,
        permutation_config=validation_permutation_config,
    )

    comparison_results: list[StrategyComparisonResult] = []
    validation_artifacts: dict[str, ValidationArtifactReceipt] = {}
    for strategy_family in comparison_config.strategy_families:
        validation_result, validation_artifact_receipt = run_validate_search_on_market_data(
            data_spec=comparison_config.data_spec,
            parameter_grid=strategy_family.parameter_grid,
            split_ratio=comparison_config.split_config.split_ratio,
            strategy_name=strategy_family.strategy_name,
            backtest_config=backtest_config,
            output_dir=strategy_output_root,
            experiment_name=strategy_family.strategy_name,
            max_drawdown_cap=comparison_config.max_drawdown_cap,
            min_trade_count=comparison_config.min_trade_count,
            holdout_cutoff_date=comparison_config.holdout_cutoff_date,
            policy_config=comparison_config.research_policy_config,
            permutation_config=validation_permutation_config,
        )
        if validation_artifact_receipt is not None:
            validation_artifacts[strategy_family.strategy_name] = validation_artifact_receipt
        comparison_results.append(
            _build_strategy_comparison_result(
                validation_result=validation_result,
                validation_artifact_receipt=validation_artifact_receipt,
            )
        )

    comparison_results = sorted(comparison_results, key=_strategy_comparison_ranking_key)
    summary = StrategyComparisonSummary(
        data_spec=comparison_config.data_spec,
        split_config=comparison_config.split_config,
        backtest_config=backtest_config,
        strategy_families=list(comparison_config.strategy_families),
        permutation_config=validation_permutation_config,
        research_policy_config=_serialize_research_policy_config(resolved_research_policy_config),
        comparison_results=comparison_results,
        metadata={
            "comparison_result_count": len(comparison_results),
            "ranking_contract": "research_policy_verdict_group_then_descending_test_score",
            "failure_behavior": "fail_fast",
        },
    )
    artifact_receipt = None
    if comparison_root is not None:
        summary, artifact_receipt = save_strategy_comparison_summary(
            comparison_root,
            summary,
            strategy_validation_artifacts=validation_artifacts,
        )
    return StrategyComparisonExecutionOutput(
        comparison_summary=summary,
        artifact_receipt=artifact_receipt,
    )


def run_walk_forward_search_with_details_workflow(
    data_spec: DataSpec,
    parameter_grid: ParameterGrid,
    train_size: int,
    test_size: int,
    step_size: int,
    strategy_name: str = "ma_crossover",
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "walk_forward_experiment",
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
    holdout_cutoff_date: str | None = None,
) -> WalkForwardExecutionOutput:
    walk_forward_result, walk_forward_artifact_receipt = run_walk_forward_search_on_market_data(
        data_spec=data_spec,
        parameter_grid=parameter_grid,
        train_size=train_size,
        test_size=test_size,
        step_size=step_size,
        strategy_name=strategy_name,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
        holdout_cutoff_date=holdout_cutoff_date,
    )
    return WalkForwardExecutionOutput(
        walk_forward_result=walk_forward_result,
        artifact_receipt=walk_forward_artifact_receipt,
    )


def run_walk_forward_search_on_market_data(
    data_spec: DataSpec,
    parameter_grid: ParameterGrid,
    train_size: int,
    test_size: int,
    step_size: int,
    strategy_name: str = "ma_crossover",
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "walk_forward_experiment",
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
    holdout_cutoff_date: str | None = None,
) -> tuple[WalkForwardResult, WalkForwardArtifactReceipt | None]:
    backtest_config = resolve_backtest_config(backtest_config)
    market_data = load_market_data(data_spec)
    market_data = _apply_holdout_cutoff_if_requested(market_data, holdout_cutoff_date)
    folds = generate_walk_forward_folds(market_data, train_size=train_size, test_size=test_size, step_size=step_size)
    validate_train_windows(strategy_name, market_data.iloc[:train_size].reset_index(drop=True), parameter_grid)

    walk_forward_root = workflow_root(output_dir, experiment_name)
    fold_results: list[WalkForwardFoldResult] = []
    for fold_index, (train_start_idx, train_end_idx, test_end_idx) in enumerate(folds, start=1):
        train_data = market_data.iloc[train_start_idx:train_end_idx].reset_index(drop=True)
        test_data = market_data.iloc[train_end_idx:test_end_idx].reset_index(drop=True)
        train_data.attrs.update(market_data.attrs)
        test_data.attrs.update(market_data.attrs)
        validate_train_windows(strategy_name, train_data, parameter_grid)
        fold_root = (walk_forward_root / "folds" / f"fold_{fold_index:03d}") if walk_forward_root is not None else None

        search_execution = run_search_on_market_data(
            market_data=train_data,
            data_spec=data_spec,
            parameter_grid=parameter_grid,
            strategy_name=strategy_name,
            backtest_config=backtest_config,
            output_dir=fold_root,
            experiment_name="train_search",
            max_drawdown_cap=max_drawdown_cap,
            min_trade_count=min_trade_count,
            generate_best_report=False,
        )
        ranked = search_execution.ranked_results
        if not ranked:
            raise ValueError(f"No train-fold results remain after ranking and threshold filters for fold {fold_index}")

        best_ranked_result = select_best_result(ranked)
        assert best_ranked_result is not None
        selected_strategy_spec = best_ranked_result.strategy_spec
        test_execution = run_experiment_on_market_data(
            market_data=test_data,
            data_spec=data_spec,
            strategy_spec=selected_strategy_spec,
            backtest_config=backtest_config,
            output_dir=fold_root,
            experiment_name="test_selected",
        )
        test_result = test_execution.result
        fold_candidate_artifact_paths: dict[str, str] = {}
        if fold_root is not None:
            fold_candidate_artifact_paths["fold_root"] = str(fold_root)
        if search_execution.artifact_receipt is not None:
            if search_execution.artifact_receipt.search_root is not None:
                fold_candidate_artifact_paths["train_search_root"] = str(search_execution.artifact_receipt.search_root)
            if search_execution.artifact_receipt.ranked_results_path is not None:
                fold_candidate_artifact_paths["train_search_ranked_results_path"] = str(search_execution.artifact_receipt.ranked_results_path)
            if search_execution.artifact_receipt.best_report_path is not None:
                fold_candidate_artifact_paths["train_search_best_report_path"] = str(search_execution.artifact_receipt.best_report_path)
            if search_execution.artifact_receipt.comparison_report_path is not None:
                fold_candidate_artifact_paths["train_search_comparison_report_path"] = str(search_execution.artifact_receipt.comparison_report_path)
        if test_execution.artifact_receipt is not None:
            fold_candidate_artifact_paths["test_selected_run_dir"] = str(test_execution.artifact_receipt.run_dir)
            fold_candidate_artifact_paths["test_selected_equity_curve_path"] = str(test_execution.artifact_receipt.equity_curve_path)
            fold_candidate_artifact_paths["test_selected_trade_log_path"] = str(test_execution.artifact_receipt.trade_log_path)
            fold_candidate_artifact_paths["test_selected_metrics_summary_path"] = str(test_execution.artifact_receipt.metrics_summary_path)
        fold_candidate_evidence = build_candidate_evidence_summary(
            strategy_spec=selected_strategy_spec,
            train_result=best_ranked_result,
            test_result=test_result,
            search_summary=search_execution.summary,
            benchmark_summary=normalize_benchmark_summary(test_result.metadata.get("benchmark_summary")),
            artifact_paths=fold_candidate_artifact_paths,
            metadata=build_holdout_metadata(train_data),
        )
        fold_candidate_decision = evaluate_candidate_policy(fold_candidate_evidence, policy_scope="walk-forward")
        fold_candidate_evidence = apply_policy_decision(fold_candidate_evidence, fold_candidate_decision)
        fold_results.append(
            WalkForwardFoldResult(
                fold_index=fold_index,
                train_start=str(train_data["datetime"].iloc[0]),
                train_end=str(train_data["datetime"].iloc[-1]),
                test_start=str(test_data["datetime"].iloc[0]),
                test_end=str(test_data["datetime"].iloc[-1]),
                selected_strategy_spec=selected_strategy_spec,
                train_best_result=best_ranked_result,
                test_result=test_result,
                test_benchmark_summary=normalize_benchmark_summary(test_result.metadata.get("benchmark_summary")),
                candidate_evidence=fold_candidate_evidence,
                candidate_decision=fold_candidate_decision,
            )
        )

    walk_forward_evidence_paths: dict[str, str] = {}
    if walk_forward_root is not None:
        walk_forward_evidence_paths["walk_forward_summary_path"] = str(walk_forward_root / WALK_FORWARD_SUMMARY_FILENAME)
        walk_forward_evidence_paths["fold_results_path"] = str(walk_forward_root / FOLD_RESULTS_FILENAME)
    aggregate_test_metrics = aggregate_walk_forward_test_metrics(fold_results)
    aggregate_benchmark_metrics = aggregate_walk_forward_benchmark_metrics(fold_results)

    result = WalkForwardResult(
        data_spec=data_spec,
        walk_forward_config=WalkForwardConfig(
            train_size=train_size,
            test_size=test_size,
            step_size=step_size,
        ),
        folds=fold_results,
        aggregate_test_metrics=aggregate_test_metrics,
        aggregate_benchmark_metrics=aggregate_benchmark_metrics,
        walk_forward_evidence=build_walk_forward_evidence_summary(
            fold_count=len(fold_results),
            validated_fold_count=len(fold_results),
            skipped_fold_count=0,
            aggregate_test_metrics=aggregate_test_metrics,
            aggregate_benchmark_metrics=aggregate_benchmark_metrics,
            artifact_paths=walk_forward_evidence_paths,
            metadata=build_holdout_metadata(market_data),
        ),
        walk_forward_decision=None,
        metadata={"fold_count": len(fold_results), **build_holdout_metadata(market_data)},
    )
    walk_forward_decision = evaluate_walk_forward_policy(result.walk_forward_evidence)
    walk_forward_evidence = apply_policy_decision(result.walk_forward_evidence, walk_forward_decision)
    result = replace(
        result,
        walk_forward_evidence=walk_forward_evidence,
        walk_forward_decision=walk_forward_decision,
    )
    walk_forward_artifact_receipt: WalkForwardArtifactReceipt | None = None
    if walk_forward_root is not None:
        result, walk_forward_artifact_receipt = save_walk_forward_result(walk_forward_root, result)
    return result, walk_forward_artifact_receipt


def _build_search_summary(search_space: SearchSpaceEvaluation, ranked_results: list[ExperimentResult], top_n: int = 3) -> SearchSummary:
    top_results = select_top_results(ranked_results, limit=top_n)
    best_result = top_results[0] if top_results else None
    return SearchSummary(
        strategy_name=search_space.strategy_name,
        search_parameter_names=list(search_space.parameter_names),
        attempted_combinations=search_space.attempted_combination_count,
        valid_combinations=search_space.valid_combination_count,
        invalid_combinations=search_space.invalid_combination_count,
        result_count=len(ranked_results),
        ranking_score=RANKING_SCORE_FIELD,
        best_result=best_result,
        top_results=top_results,
    )


def _resolve_research_policy_config(
    *,
    policy_config: ResearchPolicyConfig | None,
    max_drawdown_cap: float | None,
    min_trade_count: int | None,
    permutation_config: ValidationPermutationConfig,
) -> ResearchPolicyConfig:
    if policy_config is not None:
        return policy_config
    if permutation_config.enabled:
        return ResearchPolicyConfig(
            max_reruns=0,
            min_trade_count=min_trade_count if min_trade_count is not None else 1,
            max_drawdown_cap=max_drawdown_cap,
            min_return_degradation=0.0,
            required_permutation_null_model=permutation_config.null_model,
            required_permutation_scope=permutation_config.scope,
        )
    return ResearchPolicyConfig(
        max_reruns=0,
        min_trade_count=min_trade_count if min_trade_count is not None else 1,
        max_drawdown_cap=max_drawdown_cap,
        min_return_degradation=0.0,
        max_permutation_p_value=None,
        required_permutation_null_model=None,
        required_permutation_scope=None,
    )


def _serialize_research_policy_config(config: ResearchPolicyConfig) -> dict[str, object]:
    return {
        "max_reruns": config.max_reruns,
        "min_trade_count": config.min_trade_count,
        "max_drawdown_cap": config.max_drawdown_cap,
        "min_return_degradation": config.min_return_degradation,
        "max_permutation_p_value": config.max_permutation_p_value,
        "required_permutation_null_model": config.required_permutation_null_model,
        "required_permutation_scope": config.required_permutation_scope,
    }


def _run_validation_permutation_diagnostic(
    *,
    data_spec: DataSpec,
    selected_strategy_spec: StrategySpec,
    backtest_config: BacktestConfig,
    test_data: pd.DataFrame,
    validation_root: Path | None,
    permutation_config: ValidationPermutationConfig,
) -> tuple[PermutationTestSummary | None, PermutationTestArtifactReceipt | None, bool]:
    try:
        execution = run_permutation_test_with_details(
            data_spec=data_spec,
            strategy_spec=selected_strategy_spec,
            permutation_count=permutation_config.permutations,
            block_size=permutation_config.block_size,
            target_metric_name=permutation_config.target_metric_name,
            seed=permutation_config.seed,
            backtest_config=backtest_config,
            output_dir=validation_root,
            experiment_name="permutation_test",
            market_data=test_data,
            permutation_scope=permutation_config.scope,
        )
    except Exception:
        return None, None, True
    return execution.permutation_test_summary, execution.artifact_receipt, False


def _classify_validation_permutation_status(
    *,
    permutation_summary: PermutationTestSummary | None,
    permutation_config: ValidationPermutationConfig,
    research_policy_config: ResearchPolicyConfig,
    execution_error: bool,
) -> ValidationPermutationStatus:
    if not permutation_config.enabled:
        return "skipped"
    if execution_error or permutation_summary is None:
        return "error"
    empirical_p_value = permutation_summary.empirical_p_value
    if empirical_p_value is None:
        return "error"
    if research_policy_config.max_permutation_p_value is not None and empirical_p_value > research_policy_config.max_permutation_p_value:
        return "completed_failed"
    if (
        research_policy_config.required_permutation_null_model is not None
        and permutation_summary.null_model != research_policy_config.required_permutation_null_model
    ):
        return "error"
    if (
        research_policy_config.required_permutation_scope is not None
        and permutation_summary.metadata.get("permutation_scope", "candidate_fixed") != research_policy_config.required_permutation_scope
    ):
        return "error"
    return "completed_passed"


def _validate_strategy_comparison_families(comparison_config: StrategyComparisonConfig) -> None:
    if not comparison_config.strategy_families:
        raise ValueError("Strategy comparison requires at least one strategy family")
    seen: set[str] = set()
    for strategy_family in comparison_config.strategy_families:
        get_strategy_registration(strategy_family.strategy_name)
        if strategy_family.strategy_name in seen:
            raise ValueError(f"Duplicate strategy family in comparison: {strategy_family.strategy_name}")
        seen.add(strategy_family.strategy_name)


def _build_strategy_comparison_result(
    *,
    validation_result: ValidationResult,
    validation_artifact_receipt: ValidationArtifactReceipt | None,
) -> StrategyComparisonResult:
    candidate_evidence = validation_result.candidate_evidence
    artifact_paths = dict(candidate_evidence.artifact_paths if candidate_evidence is not None else {})
    if validation_artifact_receipt is not None:
        artifact_paths.update(
            {
                key: value
                for key, value in (serialize_validation_artifact_receipt(validation_artifact_receipt) or {}).items()
                if isinstance(value, str)
            }
        )
    return StrategyComparisonResult(
        strategy_name=validation_result.selected_strategy_spec.name,
        selected_strategy_spec=validation_result.selected_strategy_spec,
        validation_result=validation_result,
        train_score=validation_result.train_best_result.score,
        test_score=validation_result.test_result.score,
        permutation_status=candidate_evidence.permutation_status if candidate_evidence is not None else "skipped",
        research_policy_verdict=getattr(validation_result.research_policy_decision, "verdict", None),
        candidate_policy_verdict=validation_result.candidate_decision.verdict
        if validation_result.candidate_decision is not None
        else None,
        artifact_paths=artifact_paths,
    )


def _strategy_comparison_ranking_key(result: StrategyComparisonResult) -> tuple[int, float, str]:
    verdict_rank = {
        "promote": 0,
        "blocked": 1,
        "reject": 2,
    }.get(result.research_policy_verdict, 3)
    return (verdict_rank, -result.test_score, result.strategy_name)


def _build_research_policy_candidate_id(
    selected_strategy_spec: StrategySpec,
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
) -> str:
    parameter_items = ",".join(f"{key}={value}" for key, value in sorted(selected_strategy_spec.parameters.items()))
    return (
        f"{selected_strategy_spec.name}:"
        f"{parameter_items}:"
        f"{train_data['datetime'].iloc[0]}-{test_data['datetime'].iloc[-1]}"
    )


def _apply_holdout_cutoff_if_requested(
    market_data: pd.DataFrame,
    holdout_cutoff_date: str | None,
) -> pd.DataFrame:
    if holdout_cutoff_date is None:
        return market_data
    development_data, _ = split_holdout_data(market_data, holdout_cutoff_date)
    return development_data
