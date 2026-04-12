from __future__ import annotations

"""Presentation boundary for search-specific report artifacts.

This module prepares and writes HTML report artifacts for search workflows.
It may consume storage-owned artifact receipts, but it does not own canonical
persisted experiment artifacts or filename/layout decisions for raw outputs.
"""

from pathlib import Path

import pandas as pd

from .report import (
    ExperimentReportInput,
    SearchReportLinkContext,
    render_experiment_report,
    render_search_comparison_report,
    save_experiment_report,
)
from .benchmark import build_buy_and_hold_equity_curve, summarize_buy_and_hold
from .schemas import EquityCurveFrame, ExperimentResult
from .storage import ArtifactReceipt

BEST_REPORT_FILENAME = "best_report.html"
SEARCH_REPORT_FILENAME = "search_report.html"


def save_best_search_report(
    search_root: Path,
    best_result: ExperimentResult,
    artifact_receipt: ArtifactReceipt | None,
) -> Path:
    if artifact_receipt is None:
        raise ValueError("Best search result is missing saved artifacts required for report generation")

    equity_curve = pd.read_csv(artifact_receipt.equity_curve_path)
    trades = pd.read_csv(artifact_receipt.trade_log_path)
    benchmark_summary = summarize_buy_and_hold(equity_curve, best_result.backtest_config.initial_capital)
    benchmark_curve = build_buy_and_hold_equity_curve(equity_curve, best_result.backtest_config.initial_capital)
    report_content = render_experiment_report(
        ExperimentReportInput(
            result=best_result,
            equity_curve=equity_curve,
            trades=trades,
            benchmark_summary=benchmark_summary,
            benchmark_curve=benchmark_curve,
        )
    )
    return save_experiment_report(report_content, search_root / BEST_REPORT_FILENAME)


def save_search_comparison_report(
    search_root: Path,
    ranked_results: list[ExperimentResult],
    artifact_receipts: list[ArtifactReceipt | None],
    best_report_path: Path | None,
    top_n: int = 5,
) -> Path:
    top_equity_curves = load_top_search_equity_curves(artifact_receipts, ranked_results, top_n=top_n)
    report_content = render_search_comparison_report(
        link_context=SearchReportLinkContext(
            link_base_dir=search_root,
            search_display_name=search_root.name,
        ),
        ranked_results=ranked_results,
        artifact_receipts=artifact_receipts,
        top_equity_curves=top_equity_curves,
        best_report_path=best_report_path,
    )
    return save_experiment_report(report_content, search_root / SEARCH_REPORT_FILENAME)


def load_top_search_equity_curves(
    artifact_receipts: list[ArtifactReceipt | None],
    ranked_results: list[ExperimentResult],
    top_n: int,
) -> dict[str, EquityCurveFrame]:
    top_equity_curves: dict[str, EquityCurveFrame] = {}
    for rank, (result, artifact_receipt) in enumerate(zip(ranked_results[:top_n], artifact_receipts[:top_n], strict=False), start=1):
        if artifact_receipt is None:
            raise ValueError("Ranked search result is missing saved equity curve required for comparison report generation")
        label = build_search_curve_label(rank, result)
        top_equity_curves[label] = pd.read_csv(artifact_receipt.equity_curve_path)
    return top_equity_curves


def build_search_curve_label(rank: int, result: ExperimentResult) -> str:
    parameters = result.strategy_spec.parameters
    short_window = parameters.get("short_window", "")
    long_window = parameters.get("long_window", "")
    return f"Rank {rank} | SW {short_window} | LW {long_window}"
