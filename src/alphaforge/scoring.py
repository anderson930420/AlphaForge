from __future__ import annotations

from collections.abc import Iterable

from .schemas import ExperimentResult, MetricReport


def passes_thresholds(
    metrics: MetricReport,
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
) -> bool:
    if max_drawdown_cap is not None and metrics.max_drawdown < -abs(max_drawdown_cap):
        return False
    if min_trade_count is not None and metrics.trade_count < min_trade_count:
        return False
    return True


def score_metrics(metrics: MetricReport) -> float:
    drawdown_penalty = abs(metrics.max_drawdown) * 2.0
    turnover_penalty = metrics.turnover * 0.01
    return (
        metrics.annualized_return
        + (metrics.sharpe_ratio * 0.2)
        + (metrics.win_rate * 0.1)
        - drawdown_penalty
        - turnover_penalty
    )


def rank_results(
    results: Iterable[ExperimentResult],
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
) -> list[ExperimentResult]:
    filtered = [
        result
        for result in results
        if passes_thresholds(result.metrics, max_drawdown_cap=max_drawdown_cap, min_trade_count=min_trade_count)
    ]
    return sorted(filtered, key=lambda item: item.score, reverse=True)


def select_best_result(
    results: Iterable[ExperimentResult],
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
) -> ExperimentResult | None:
    ranked = rank_results(
        results,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
    )
    return ranked[0] if ranked else None
