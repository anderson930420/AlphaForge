from __future__ import annotations

from .schemas import WalkForwardFoldResult


def aggregate_walk_forward_test_metrics(folds: list[WalkForwardFoldResult]) -> dict[str, float | int]:
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


def aggregate_walk_forward_benchmark_metrics(folds: list[WalkForwardFoldResult]) -> dict[str, float | int]:
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
