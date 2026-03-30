from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config
from .backtest import run_backtest
from .benchmark import summarize_buy_and_hold
from .data_loader import load_market_data
from .metrics import compute_metrics
from .report import render_experiment_report, render_search_comparison_report, save_experiment_report
from .scoring import rank_results, score_metrics
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
    save_ranked_results_artifact,
    save_ranked_results_with_columns,
    save_single_experiment,
    save_validation_result,
    save_walk_forward_result,
)
from .strategy.ma_crossover import MovingAverageCrossoverStrategy


def run_experiment(
    data_spec: DataSpec,
    strategy_spec: StrategySpec,
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = "single_experiment",
) -> tuple[ExperimentResult, EquityCurveFrame, object]:
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
) -> tuple[ExperimentResult, EquityCurveFrame, pd.DataFrame]:
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
        result = save_single_experiment(output_dir, experiment_name, result, equity_curve, trades)
    return result, equity_curve, trades


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
) -> list[ExperimentResult]:
    results: list[ExperimentResult] = []
    strategy_specs = build_strategy_specs("ma_crossover", parameter_grid)
    search_root = (output_dir / experiment_name) if output_dir is not None else None
    runs_output_dir = (search_root / "runs") if search_root is not None else None
    for index, strategy_spec in enumerate(strategy_specs, start=1):
        result, _, _ = _run_experiment_on_market_data(
            market_data=market_data,
            data_spec=data_spec,
            strategy_spec=strategy_spec,
            backtest_config=backtest_config,
            output_dir=runs_output_dir,
            experiment_name=f"run_{index:03d}",
        )
        results.append(result)

    ranked = rank_results(
        results,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
    )
    if output_dir is not None:
        parameter_columns = list(parameter_grid)
        save_ranked_results_with_columns(search_root, ranked, parameter_columns=parameter_columns)
        if generate_best_report:
            best_report_path = _save_best_search_report(search_root=search_root, best_result=ranked[0]) if ranked else None
            _save_search_comparison_report(search_root=search_root, ranked_results=ranked, best_report_path=best_report_path)
    return ranked


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
    ranked = _run_search_on_market_data(
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
        train_best_result, _, _ = _run_experiment_on_market_data(
            market_data=train_data,
            data_spec=data_spec,
            strategy_spec=selected_strategy_spec,
            backtest_config=backtest_config,
            output_dir=validation_root,
            experiment_name="train_best",
        )
    test_result, _, _ = _run_experiment_on_market_data(
        market_data=test_data,
        data_spec=data_spec,
        strategy_spec=selected_strategy_spec,
        backtest_config=backtest_config,
        output_dir=validation_root,
        experiment_name="test_selected",
    )

    validation_result = ValidationResult(
        data_spec=data_spec,
        split_config=ValidationSplitConfig(split_ratio=split_ratio),
        selected_strategy_spec=selected_strategy_spec,
        train_best_result=train_best_result,
        test_result=test_result,
        test_benchmark_summary=_extract_benchmark_summary(test_result),
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

        ranked = _run_search_on_market_data(
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
        if not ranked:
            raise ValueError(f"No train-fold results remain after ranking and threshold filters for fold {fold_index}")

        selected_strategy_spec = ranked[0].strategy_spec
        test_result, _, _ = _run_experiment_on_market_data(
            market_data=test_data,
            data_spec=data_spec,
            strategy_spec=selected_strategy_spec,
            backtest_config=backtest_config,
            output_dir=test_output_dir,
            experiment_name="test_selected",
        )
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
                test_benchmark_summary=_extract_benchmark_summary(test_result),
                fold_path=fold_root,
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
        aggregate_test_metrics=_aggregate_walk_forward_test_metrics(fold_results),
        aggregate_benchmark_metrics=_aggregate_walk_forward_benchmark_metrics(fold_results),
        metadata={"fold_count": len(fold_results)},
    )
    if walk_forward_root is not None:
        result = save_walk_forward_result(walk_forward_root, result)
    return result


def build_strategy(strategy_spec: StrategySpec) -> MovingAverageCrossoverStrategy:
    if strategy_spec.name != "ma_crossover":
        raise ValueError(f"Unsupported strategy: {strategy_spec.name}")
    return MovingAverageCrossoverStrategy(strategy_spec)


def _save_best_search_report(search_root: Path, best_result: ExperimentResult) -> Path:
    if best_result.equity_curve_path is None or best_result.trade_log_path is None:
        raise ValueError("Best search result is missing saved artifacts required for report generation")

    equity_curve = pd.read_csv(best_result.equity_curve_path)
    trades = pd.read_csv(best_result.trade_log_path)
    report_content = render_experiment_report(best_result, equity_curve, trades)
    return save_experiment_report(report_content, search_root / "best_report.html")


def _save_search_comparison_report(
    search_root: Path,
    ranked_results: list[ExperimentResult],
    best_report_path: Path | None,
    top_n: int = 5,
) -> Path:
    top_equity_curves = _load_top_search_equity_curves(ranked_results, top_n=top_n)
    report_content = render_search_comparison_report(
        search_root=search_root,
        ranked_results=ranked_results,
        top_equity_curves=top_equity_curves,
        best_report_path=best_report_path,
    )
    return save_experiment_report(report_content, search_root / "search_report.html")


def _load_top_search_equity_curves(
    ranked_results: list[ExperimentResult],
    top_n: int,
) -> dict[str, EquityCurveFrame]:
    top_equity_curves: dict[str, EquityCurveFrame] = {}
    for rank, result in enumerate(ranked_results[:top_n], start=1):
        if result.equity_curve_path is None:
            raise ValueError("Ranked search result is missing saved equity curve required for comparison report generation")
        label = _build_search_curve_label(rank, result)
        top_equity_curves[label] = pd.read_csv(result.equity_curve_path)
    return top_equity_curves


def _build_search_curve_label(rank: int, result: ExperimentResult) -> str:
    parameters = result.strategy_spec.parameters
    short_window = parameters.get("short_window", "")
    long_window = parameters.get("long_window", "")
    return f"Rank {rank} | SW {short_window} | LW {long_window}"


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


def _aggregate_walk_forward_test_metrics(folds: list[WalkForwardFoldResult]) -> dict[str, float | int]:
    if not folds:
        return {
            "fold_count": 0,
            "mean_test_total_return": 0.0,
            "mean_test_sharpe_ratio": 0.0,
            "mean_test_max_drawdown": 0.0,
            "worst_test_max_drawdown": 0.0,
            "mean_test_win_rate": 0.0,
            "mean_test_turnover": 0.0,
            "total_test_trade_count": 0,
        }

    test_metrics = [fold.test_result.metrics for fold in folds]
    return {
        "fold_count": len(folds),
        "mean_test_total_return": float(sum(metric.total_return for metric in test_metrics) / len(test_metrics)),
        "mean_test_sharpe_ratio": float(sum(metric.sharpe_ratio for metric in test_metrics) / len(test_metrics)),
        "mean_test_max_drawdown": float(sum(metric.max_drawdown for metric in test_metrics) / len(test_metrics)),
        "worst_test_max_drawdown": float(min(metric.max_drawdown for metric in test_metrics)),
        "mean_test_win_rate": float(sum(metric.win_rate for metric in test_metrics) / len(test_metrics)),
        "mean_test_turnover": float(sum(metric.turnover for metric in test_metrics) / len(test_metrics)),
        "total_test_trade_count": int(sum(metric.trade_count for metric in test_metrics)),
    }


def _aggregate_walk_forward_benchmark_metrics(folds: list[WalkForwardFoldResult]) -> dict[str, float | int]:
    if not folds:
        return {
            "fold_count": 0,
            "mean_benchmark_total_return": 0.0,
            "mean_benchmark_max_drawdown": 0.0,
            "mean_excess_return": 0.0,
        }

    benchmark_summaries = [fold.test_benchmark_summary for fold in folds]
    return {
        "fold_count": len(folds),
        "mean_benchmark_total_return": float(
            sum(summary.get("total_return", 0.0) for summary in benchmark_summaries) / len(benchmark_summaries)
        ),
        "mean_benchmark_max_drawdown": float(
            sum(summary.get("max_drawdown", 0.0) for summary in benchmark_summaries) / len(benchmark_summaries)
        ),
        "mean_excess_return": float(
            sum(
                fold.test_result.metrics.total_return - fold.test_benchmark_summary.get("total_return", 0.0)
                for fold in folds
            )
            / len(folds)
        ),
    }


def _extract_benchmark_summary(result: ExperimentResult) -> dict[str, float]:
    benchmark_summary = result.metadata.get("benchmark_summary", {})
    return {
        "total_return": float(benchmark_summary.get("total_return", 0.0)),
        "max_drawdown": float(benchmark_summary.get("max_drawdown", 0.0)),
    }
