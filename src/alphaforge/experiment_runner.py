from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import config
from .backtest import run_backtest
from .benchmark import build_buy_and_hold_equity_curve, normalize_benchmark_summary, summarize_buy_and_hold
from .data_loader import load_market_data
from .metrics import compute_metrics
from .report import ExperimentReportInput
from .scoring import rank_results, score_metrics
from .search_reporting import save_best_search_report, save_search_comparison_report
from .schemas import (
    BacktestConfig,
    DataSpec,
    EquityCurveFrame,
    ExperimentResult,
    StrategySpec,
    ValidationResult,
    ValidationSplitConfig,
    WalkForwardConfig,
    WalkForwardFoldResult,
    WalkForwardResult,
)
from .search import build_strategy_specs
from .storage import (
    ArtifactReceipt,
    save_ranked_results_artifact,
    save_ranked_results_with_columns,
    save_single_experiment,
    save_validation_result,
    save_walk_forward_result,
)
from .strategy.ma_crossover import MovingAverageCrossoverStrategy
from .walk_forward_aggregation import (
    aggregate_walk_forward_benchmark_metrics,
    aggregate_walk_forward_test_metrics,
)


@dataclass(frozen=True)
class ExperimentExecutionOutput:
    """Runner-local orchestration bundle for one executed strategy run."""

    result: ExperimentResult
    equity_curve: EquityCurveFrame
    trade_log: pd.DataFrame
    report_input: ExperimentReportInput
    artifact_receipt: ArtifactReceipt | None = None


@dataclass(frozen=True)
class SearchExecutionOutput:
    """Runner-local orchestration bundle for ranked search plus saved artifact refs."""

    ranked_results: list[ExperimentResult]
    ranked_results_path: Path | None = None
    best_report_path: Path | None = None
    comparison_report_path: Path | None = None


def run_experiment(
    data_spec: DataSpec,
    strategy_spec: StrategySpec,
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "single_experiment",
) -> tuple[ExperimentResult, EquityCurveFrame, object]:
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
    backtest_config = backtest_config or BacktestConfig(
        initial_capital=config.INITIAL_CAPITAL,
        fee_rate=config.DEFAULT_FEE_RATE,
        slippage_rate=config.DEFAULT_SLIPPAGE_RATE,
        annualization_factor=config.DEFAULT_ANNUALIZATION,
    )
    market_data = load_market_data(data_spec)
    return _run_experiment_on_market_data(
        market_data=market_data,
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
    )


def _run_experiment_on_market_data(
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
        metadata={
            "missing_data_policy": market_data.attrs.get("missing_data_policy", ""),
            "benchmark_summary": benchmark_summary,
        },
    )
    if output_dir is not None:
        result, receipt = save_single_experiment(output_dir, experiment_name, result, equity_curve, trades)
    report_input = ExperimentReportInput(
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
    backtest_config = backtest_config or BacktestConfig(
        initial_capital=config.INITIAL_CAPITAL,
        fee_rate=config.DEFAULT_FEE_RATE,
        slippage_rate=config.DEFAULT_SLIPPAGE_RATE,
        annualization_factor=config.DEFAULT_ANNUALIZATION,
    )
    market_data = load_market_data(data_spec)
    return _run_search_on_market_data(
        market_data=market_data,
        data_spec=data_spec,
        parameter_grid=parameter_grid,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
        generate_best_report=generate_best_report,
    )


def _run_search_on_market_data(
    market_data: pd.DataFrame,
    data_spec: DataSpec,
    parameter_grid: dict[str, list[int]],
    backtest_config: BacktestConfig,
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
    strategy_specs = build_strategy_specs("ma_crossover", parameter_grid)
    search_root = (output_dir / experiment_name) if output_dir is not None else None
    runs_output_dir = (search_root / "runs") if search_root is not None else None
    for index, strategy_spec in enumerate(strategy_specs, start=1):
        execution = _run_experiment_on_market_data(
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
    if output_dir is not None:
        parameter_columns = list(parameter_grid)
        ranked_results_path = save_ranked_results_with_columns(search_root, ranked, parameter_columns=parameter_columns)
        ranked_receipts = [artifact_receipts_by_result_id.get(id(result)) for result in ranked]
        if generate_best_report:
            best_receipt = ranked_receipts[0] if ranked_receipts else None
            best_report_path = (
                save_best_search_report(search_root=search_root, best_result=ranked[0], artifact_receipt=best_receipt)
                if ranked
                else None
            )
            comparison_report_path = save_search_comparison_report(
                search_root=search_root,
                ranked_results=ranked,
                artifact_receipts=ranked_receipts,
                best_report_path=best_report_path,
            )
    return SearchExecutionOutput(
        ranked_results=ranked,
        ranked_results_path=ranked_results_path,
        best_report_path=best_report_path,
        comparison_report_path=comparison_report_path,
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
    backtest_config = backtest_config or BacktestConfig(
        initial_capital=config.INITIAL_CAPITAL,
        fee_rate=config.DEFAULT_FEE_RATE,
        slippage_rate=config.DEFAULT_SLIPPAGE_RATE,
        annualization_factor=config.DEFAULT_ANNUALIZATION,
    )
    market_data = load_market_data(data_spec)
    train_data, test_data = _split_market_data_by_ratio(market_data, split_ratio)
    _validate_train_windows(train_data, parameter_grid)

    validation_root = (output_dir / experiment_name) if output_dir is not None else None
    search_execution = _run_search_on_market_data(
        market_data=train_data,
        data_spec=data_spec,
        parameter_grid=parameter_grid,
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

    selected_strategy_spec = ranked[0].strategy_spec
    train_best_result = ranked[0]
    train_ranked_results_path = None
    if validation_root is not None:
        train_ranked_results_path = save_ranked_results_artifact(
            output_dir=validation_root,
            results=ranked,
            parameter_columns=list(parameter_grid),
            filename="train_ranked_results.csv",
        )
        train_best_execution = _run_experiment_on_market_data(
            market_data=train_data,
            data_spec=data_spec,
            strategy_spec=selected_strategy_spec,
            backtest_config=backtest_config,
            output_dir=validation_root,
            experiment_name="train_best",
        )
        train_best_result = train_best_execution.result
    test_execution = _run_experiment_on_market_data(
        market_data=test_data,
        data_spec=data_spec,
        strategy_spec=selected_strategy_spec,
        backtest_config=backtest_config,
        output_dir=validation_root,
        experiment_name="test_selected",
    )
    test_result = test_execution.result

    validation_result = ValidationResult(
        data_spec=data_spec,
        split_config=ValidationSplitConfig(split_ratio=split_ratio),
        selected_strategy_spec=selected_strategy_spec,
        train_best_result=train_best_result,
        test_result=test_result,
        test_benchmark_summary=normalize_benchmark_summary(test_result.metadata.get("benchmark_summary")),
        train_ranked_results_path=train_ranked_results_path,
        metadata=_build_validation_metadata(train_data, test_data),
    )
    if validation_root is not None:
        validation_result = save_validation_result(validation_root, validation_result)
    return validation_result


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
    backtest_config = backtest_config or BacktestConfig(
        initial_capital=config.INITIAL_CAPITAL,
        fee_rate=config.DEFAULT_FEE_RATE,
        slippage_rate=config.DEFAULT_SLIPPAGE_RATE,
        annualization_factor=config.DEFAULT_ANNUALIZATION,
    )
    market_data = load_market_data(data_spec)
    folds = _generate_walk_forward_folds(market_data, train_size=train_size, test_size=test_size, step_size=step_size)
    _validate_train_windows(market_data.iloc[:train_size].reset_index(drop=True), parameter_grid)

    walk_forward_root = (output_dir / experiment_name) if output_dir is not None else None
    fold_results: list[WalkForwardFoldResult] = []
    for fold_index, (train_start_idx, train_end_idx, test_end_idx) in enumerate(folds, start=1):
        train_data = market_data.iloc[train_start_idx:train_end_idx].reset_index(drop=True)
        test_data = market_data.iloc[train_end_idx:test_end_idx].reset_index(drop=True)
        _validate_train_windows(train_data, parameter_grid)
        fold_root = (walk_forward_root / "folds" / f"fold_{fold_index:03d}") if walk_forward_root is not None else None
        train_output_dir = fold_root
        test_output_dir = fold_root

        search_execution = _run_search_on_market_data(
            market_data=train_data,
            data_spec=data_spec,
            parameter_grid=parameter_grid,
            backtest_config=backtest_config,
            output_dir=train_output_dir,
            experiment_name="train_search",
            max_drawdown_cap=max_drawdown_cap,
            min_trade_count=min_trade_count,
            generate_best_report=False,
        )
        ranked = search_execution.ranked_results
        if not ranked:
            raise ValueError(f"No train-fold results remain after ranking and threshold filters for fold {fold_index}")

        selected_strategy_spec = ranked[0].strategy_spec
        test_execution = _run_experiment_on_market_data(
            market_data=test_data,
            data_spec=data_spec,
            strategy_spec=selected_strategy_spec,
            backtest_config=backtest_config,
            output_dir=test_output_dir,
            experiment_name="test_selected",
        )
        test_result = test_execution.result
        fold_results.append(
            WalkForwardFoldResult(
                fold_index=fold_index,
                train_start=str(train_data["datetime"].iloc[0]),
                train_end=str(train_data["datetime"].iloc[-1]),
                test_start=str(test_data["datetime"].iloc[0]),
                test_end=str(test_data["datetime"].iloc[-1]),
                selected_strategy_spec=selected_strategy_spec,
                train_best_result=ranked[0],
                test_result=test_result,
                test_benchmark_summary=normalize_benchmark_summary(test_result.metadata.get("benchmark_summary")),
            )
        )

    result = WalkForwardResult(
        data_spec=data_spec,
        walk_forward_config=WalkForwardConfig(
            train_size=train_size,
            test_size=test_size,
            step_size=step_size,
        ),
        folds=fold_results,
        aggregate_test_metrics=aggregate_walk_forward_test_metrics(fold_results),
        aggregate_benchmark_metrics=aggregate_walk_forward_benchmark_metrics(fold_results),
        metadata={"fold_count": len(fold_results)},
    )
    if walk_forward_root is not None:
        result = save_walk_forward_result(walk_forward_root, result)
    return result


def build_strategy(strategy_spec: StrategySpec) -> MovingAverageCrossoverStrategy:
    if strategy_spec.name != "ma_crossover":
        raise ValueError(f"Unsupported strategy: {strategy_spec.name}")
    return MovingAverageCrossoverStrategy(strategy_spec)


def _split_market_data_by_ratio(market_data: pd.DataFrame, split_ratio: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    if split_ratio <= 0.0 or split_ratio >= 1.0:
        raise ValueError("split_ratio must be between 0 and 1")

    split_index = int(len(market_data) * split_ratio)
    if split_index <= 0 or split_index >= len(market_data):
        raise ValueError("split_ratio creates an empty train or test segment")

    train_data = market_data.iloc[:split_index].reset_index(drop=True)
    test_data = market_data.iloc[split_index:].reset_index(drop=True)
    if train_data.empty or test_data.empty:
        raise ValueError("split_ratio creates an empty train or test segment")
    return train_data, test_data


def _validate_train_windows(train_data: pd.DataFrame, parameter_grid: dict[str, list[int]]) -> None:
    long_windows = parameter_grid.get("long_window", [])
    if not long_windows:
        return
    largest_long_window = max(int(window) for window in long_windows)
    if len(train_data) < largest_long_window:
        raise ValueError("Train segment is too short for the requested long_window values")


def _build_validation_metadata(train_data: pd.DataFrame, test_data: pd.DataFrame) -> dict[str, object]:
    return {
        "train_rows": int(len(train_data)),
        "test_rows": int(len(test_data)),
        "train_start": str(train_data["datetime"].iloc[0]),
        "train_end": str(train_data["datetime"].iloc[-1]),
        "test_start": str(test_data["datetime"].iloc[0]),
        "test_end": str(test_data["datetime"].iloc[-1]),
    }


def _generate_walk_forward_folds(
    market_data: pd.DataFrame,
    train_size: int,
    test_size: int,
    step_size: int,
) -> list[tuple[int, int, int]]:
    if train_size <= 0 or test_size <= 0 or step_size <= 0:
        raise ValueError("train_size, test_size, and step_size must be positive integers")
    if len(market_data) < train_size + test_size:
        raise ValueError("Dataset is too short for the requested train/test walk-forward windows")

    folds: list[tuple[int, int, int]] = []
    start_index = 0
    while start_index + train_size + test_size <= len(market_data):
        train_end_idx = start_index + train_size
        test_end_idx = train_end_idx + test_size
        folds.append((start_index, train_end_idx, test_end_idx))
        start_index += step_size
    if not folds:
        raise ValueError("Dataset is too short for the requested train/test walk-forward windows")
    return folds
