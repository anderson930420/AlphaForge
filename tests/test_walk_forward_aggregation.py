from __future__ import annotations

from pathlib import Path

from alphaforge.schemas import (
    BacktestConfig,
    DataSpec,
    ExperimentResult,
    MetricReport,
    StrategySpec,
    WalkForwardFoldResult,
)
from alphaforge.walk_forward_aggregation import (
    aggregate_walk_forward_benchmark_metrics,
    aggregate_walk_forward_test_metrics,
)


def _build_fold(
    fold_index: int,
    total_return: float,
    sharpe_ratio: float,
    max_drawdown: float,
    win_rate: float,
    turnover: float,
    trade_count: int,
    benchmark_total_return: float,
    benchmark_max_drawdown: float,
) -> WalkForwardFoldResult:
    result = ExperimentResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(100000.0, 0.001, 0.0005, 252),
        metrics=MetricReport(
            total_return=total_return,
            annualized_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            turnover=turnover,
            trade_count=trade_count,
        ),
        score=0.5,
    )
    return WalkForwardFoldResult(
        fold_index=fold_index,
        train_start="2024-01-01",
        train_end="2024-01-10",
        test_start="2024-01-11",
        test_end="2024-01-20",
        selected_strategy_spec=result.strategy_spec,
        train_best_result=result,
        test_result=result,
        test_benchmark_summary={
            "total_return": benchmark_total_return,
            "max_drawdown": benchmark_max_drawdown,
        },
    )


def test_aggregate_walk_forward_test_metrics_returns_expected_summary() -> None:
    folds = [
        _build_fold(1, 0.10, 1.0, -0.10, 0.50, 1.0, 2, 0.06, -0.08),
        _build_fold(2, 0.20, 1.4, -0.20, 0.75, 1.5, 4, 0.08, -0.10),
    ]

    summary = aggregate_walk_forward_test_metrics(folds)

    assert summary == {
        "fold_count": 2,
        "mean_test_total_return": 0.15000000000000002,
        "mean_test_sharpe_ratio": 1.2,
        "mean_test_max_drawdown": -0.15000000000000002,
        "worst_test_max_drawdown": -0.2,
        "mean_test_win_rate": 0.625,
        "mean_test_turnover": 1.25,
        "total_test_trade_count": 6,
    }
    assert "pooled_test_sharpe_ratio" not in summary


def test_aggregate_walk_forward_benchmark_metrics_returns_expected_summary() -> None:
    folds = [
        _build_fold(1, 0.10, 1.0, -0.10, 0.50, 1.0, 2, 0.06, -0.08),
        _build_fold(2, 0.20, 1.4, -0.20, 0.75, 1.5, 4, 0.08, -0.10),
    ]

    summary = aggregate_walk_forward_benchmark_metrics(folds)

    assert summary == {
        "fold_count": 2,
        "mean_benchmark_total_return": 0.07,
        "mean_benchmark_max_drawdown": -0.09,
        "mean_excess_return": 0.08000000000000002,
    }
