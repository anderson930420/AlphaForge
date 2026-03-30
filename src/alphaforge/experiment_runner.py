from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config
from .backtest import run_backtest
from .data_loader import load_market_data
from .metrics import compute_metrics
from .report import render_experiment_report, render_search_comparison_report, save_experiment_report
from .scoring import rank_results, score_metrics
from .schemas import BacktestConfig, DataSpec, EquityCurveFrame, ExperimentResult, StrategySpec
from .search import build_strategy_specs
from .storage import save_ranked_results_with_columns, save_single_experiment
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
    strategy = build_strategy(strategy_spec)
    target_positions = strategy.generate_signals(market_data)
    equity_curve, trades = run_backtest(market_data, target_positions, backtest_config)
    metrics = compute_metrics(equity_curve, trades, backtest_config.annualization_factor)
    result = ExperimentResult(
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        backtest_config=backtest_config,
        metrics=metrics,
        score=score_metrics(metrics),
        metadata={"missing_data_policy": market_data.attrs.get("missing_data_policy", "")},
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
    results: list[ExperimentResult] = []
    strategy_specs = build_strategy_specs("ma_crossover", parameter_grid)
    search_root = (output_dir / experiment_name) if output_dir is not None else None
    runs_output_dir = (search_root / "runs") if search_root is not None else None
    for index, strategy_spec in enumerate(strategy_specs, start=1):
        result, _, _ = run_experiment(
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
