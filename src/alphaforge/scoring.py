from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .schemas import ExperimentResult, MetricReport

RANKING_SCORE_FIELD = "score"


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
    if not isinstance(metrics.bar_count, int) or metrics.bar_count <= 0:
        raise ValueError(f"MetricReport.bar_count must be positive for scoring, got {metrics.bar_count}")
    drawdown_penalty = abs(metrics.max_drawdown) * 2.0
    turnover_per_bar = metrics.turnover / metrics.bar_count
    turnover_penalty = turnover_per_bar * 0.01
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
    return sorted(filtered, key=_result_ranking_key)


def select_top_results(
    results: Iterable[ExperimentResult],
    limit: int,
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
) -> list[ExperimentResult]:
    ranked = rank_results(
        results,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
    )
    return ranked[: max(limit, 0)]


def select_best_result(
    results: Iterable[ExperimentResult],
    max_drawdown_cap: float | None = None,
    min_trade_count: int | None = None,
) -> ExperimentResult | None:
    top_results = select_top_results(
        results,
        limit=1,
        max_drawdown_cap=max_drawdown_cap,
        min_trade_count=min_trade_count,
    )
    return top_results[0] if top_results else None


def _result_ranking_key(result: ExperimentResult) -> tuple[float, str, tuple[tuple[str, Any], ...]]:
    return (
        -result.score,
        result.strategy_spec.name,
        tuple(sorted(result.strategy_spec.parameters.items())),
    )
