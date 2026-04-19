from __future__ import annotations

"""Public runner facade and compatibility bundles for AlphaForge workflows.

This module preserves the public runner entry points used by CLI and tests
while delegating workflow implementations to ``runner_workflows.py``.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .report import ExperimentReportInput
from .schemas import (
    BacktestConfig,
    DataSpec,
    EquityCurveFrame,
    ExperimentResult,
    SearchSummary,
    StrategySpec,
    ValidationResult,
    WalkForwardResult,
)
from .storage import ArtifactReceipt, SearchArtifactReceipt, ValidationArtifactReceipt, WalkForwardArtifactReceipt


@dataclass(frozen=True)
class ExperimentExecutionOutput:
    """Public compatibility bundle for one executed strategy run."""

    result: ExperimentResult
    equity_curve: EquityCurveFrame
    trade_log: pd.DataFrame
    report_input: ExperimentReportInput
    artifact_receipt: ArtifactReceipt | None = None


@dataclass(frozen=True)
class SearchExecutionOutput:
    """Public compatibility bundle for ranked search plus artifact refs."""

    ranked_results: list[ExperimentResult]
    summary: SearchSummary
    artifact_receipt: SearchArtifactReceipt | None = None


@dataclass(frozen=True)
class ValidationExecutionOutput:
    """Public compatibility bundle for validation results and artifact refs."""

    validation_result: ValidationResult
    artifact_receipt: ValidationArtifactReceipt | None = None


@dataclass(frozen=True)
class WalkForwardExecutionOutput:
    """Public compatibility bundle for walk-forward results and artifact refs."""

    walk_forward_result: WalkForwardResult
    artifact_receipt: WalkForwardArtifactReceipt | None = None


def run_experiment(
    data_spec: DataSpec,
    strategy_spec: StrategySpec,
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "single_experiment",
) -> tuple[ExperimentResult, EquityCurveFrame, pd.DataFrame]:
    execution = run_experiment_with_artifacts(
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
    )
    return execution.result, execution.equity_curve, execution.trade_log


def run_experiment_with_artifacts(
    data_spec: DataSpec,
    strategy_spec: StrategySpec,
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "single_experiment",
) -> ExperimentExecutionOutput:
    from .runner_workflows import run_experiment_with_artifacts_workflow

    return run_experiment_with_artifacts_workflow(
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
    )


def run_search(
    data_spec: DataSpec,
    parameter_grid: dict[str, list[int]],
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "search_experiment",
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
    generate_best_report: bool = False,
) -> list[ExperimentResult]:
    return run_search_with_details(
        data_spec=data_spec,
        parameter_grid=parameter_grid,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
        generate_best_report=generate_best_report,
    ).ranked_results


def run_search_with_details(
    data_spec: DataSpec,
    parameter_grid: dict[str, list[int]],
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "search_experiment",
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
    generate_best_report: bool = False,
) -> SearchExecutionOutput:
    from .runner_workflows import run_search_with_details_workflow

    return run_search_with_details_workflow(
        data_spec=data_spec,
        parameter_grid=parameter_grid,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
        generate_best_report=generate_best_report,
    )


def run_validate_search(
    data_spec: DataSpec,
    parameter_grid: dict[str, list[int]],
    split_ratio: float,
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "validation_experiment",
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
) -> ValidationResult:
    return run_validate_search_with_details(
        data_spec=data_spec,
        parameter_grid=parameter_grid,
        split_ratio=split_ratio,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
    ).validation_result


def run_validate_search_with_details(
    data_spec: DataSpec,
    parameter_grid: dict[str, list[int]],
    split_ratio: float,
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "validation_experiment",
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
) -> ValidationExecutionOutput:
    from .runner_workflows import run_validate_search_with_details_workflow

    return run_validate_search_with_details_workflow(
        data_spec=data_spec,
        parameter_grid=parameter_grid,
        split_ratio=split_ratio,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
    )


def run_walk_forward_search(
    data_spec: DataSpec,
    parameter_grid: dict[str, list[int]],
    train_size: int,
    test_size: int,
    step_size: int,
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "walk_forward_experiment",
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
) -> WalkForwardResult:
    return run_walk_forward_search_with_details(
        data_spec=data_spec,
        parameter_grid=parameter_grid,
        train_size=train_size,
        test_size=test_size,
        step_size=step_size,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
    ).walk_forward_result


def run_walk_forward_search_with_details(
    data_spec: DataSpec,
    parameter_grid: dict[str, list[int]],
    train_size: int,
    test_size: int,
    step_size: int,
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "walk_forward_experiment",
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
) -> WalkForwardExecutionOutput:
    from .runner_workflows import run_walk_forward_search_with_details_workflow

    return run_walk_forward_search_with_details_workflow(
        data_spec=data_spec,
        parameter_grid=parameter_grid,
        train_size=train_size,
        test_size=test_size,
        step_size=step_size,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
    )
