from __future__ import annotations

"""Report assembly and export interfaces for AlphaForge experiments.

This module assembles report-ready inputs into shareable HTML artifacts. It
consumes already-computed metrics, benchmark summaries, and storage-owned
artifact refs; it should not run backtests, compute metrics, or infer workflow
layout when explicit presentation inputs are available. Figure construction
stays in :mod:`alphaforge.visualization`.
"""

from dataclasses import dataclass
from html import escape
from pathlib import Path

import pandas as pd

from .schemas import EquityCurveFrame, ExperimentResult
from .storage import ArtifactReceipt
from .visualization import (
    build_drawdown_comparison_figure,
    build_drawdown_figure,
    build_equity_comparison_figure,
    build_equity_curve_figure,
    build_price_trade_figure,
    build_strategy_benchmark_figure,
)
from .backtest import build_execution_semantics_metadata


@dataclass(frozen=True)
class SearchReportLinkContext:
    """Report-local link context for rendering search comparison reports.

    ``link_base_dir`` is the only relative-link base used by search report
    helpers. ``search_display_name`` is display-only and does not affect path
    resolution.
    """

    link_base_dir: Path
    search_display_name: str


@dataclass(frozen=True)
class ExperimentReportInput:
    """Report-local input contract for rendering a single experiment report."""

    result: ExperimentResult
    equity_curve: EquityCurveFrame
    trades: pd.DataFrame
    benchmark_summary: dict[str, float]
    benchmark_curve: EquityCurveFrame


def build_experiment_report_input(
    result: ExperimentResult,
    equity_curve: EquityCurveFrame,
    trades: pd.DataFrame,
    benchmark_summary: dict[str, float],
    benchmark_curve: EquityCurveFrame,
) -> ExperimentReportInput:
    """Assemble the canonical single-experiment report input."""
    return ExperimentReportInput(
        result=result,
        equity_curve=equity_curve,
        trades=trades,
        benchmark_summary=benchmark_summary,
        benchmark_curve=benchmark_curve,
    )


def build_search_report_link_context(search_root: Path) -> SearchReportLinkContext:
    """Assemble the canonical search-report link context from a storage-owned root."""
    return SearchReportLinkContext(link_base_dir=search_root, search_display_name=search_root.name)


def render_experiment_report(
    report_input: ExperimentReportInput,
) -> str:
    """Assemble a single-experiment HTML report from existing artifacts."""
    to_html = _load_plotly_to_html()
    execution_assumptions_rows = _build_execution_assumptions_rows(report_input.result.metadata)
    signal_metadata_rows = _build_signal_metadata_rows(report_input.result.metadata)
    data_quality_rows = _build_data_quality_rows(report_input.result.metadata)
    trade_return_rows = _build_trade_return_rows()
    metrics_rows = _build_metrics_rows(report_input.result, report_input.benchmark_summary)
    equity_figure = build_equity_curve_figure(report_input.equity_curve)
    strategy_benchmark_figure = build_strategy_benchmark_figure(report_input.equity_curve, report_input.benchmark_curve)
    drawdown_figure = build_drawdown_figure(report_input.equity_curve)
    price_trade_figure = build_price_trade_figure(report_input.equity_curve, report_input.trades)
    equity_figure_html = _render_figure_html(to_html, equity_figure, include_plotlyjs=True)
    strategy_benchmark_figure_html = _render_figure_html(to_html, strategy_benchmark_figure, include_plotlyjs=False)
    drawdown_figure_html = _render_figure_html(to_html, drawdown_figure, include_plotlyjs=False)
    price_trade_figure_html = _render_figure_html(to_html, price_trade_figure, include_plotlyjs=False)
    experiment_title = _build_experiment_title(report_input.result)

    # The report module assembles content; figure creation stays in visualization.py.
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(experiment_title)}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      background: #f7f7f7;
      color: #1f1f1f;
    }}
    main {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    h1, h2 {{
      margin-bottom: 12px;
    }}
    .meta {{
      color: #555;
      margin-bottom: 24px;
    }}
    .section {{
      background: #ffffff;
      border: 1px solid #dddddd;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
    }}
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }}
    .metric-card {{
      border: 1px solid #e6e6e6;
      border-radius: 10px;
      padding: 14px;
      background: #fafafa;
    }}
    .metric-label {{
      font-size: 0.9rem;
      color: #666666;
      margin-bottom: 6px;
    }}
    .metric-value {{
      font-size: 1.2rem;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(experiment_title)}</h1>
    <p class="meta">Strategy: {escape(report_input.result.strategy_spec.name)} | Symbol: {escape(report_input.result.data_spec.symbol)}</p>
    <section class="section">
      <h2>Execution Assumptions</h2>
      <div class="metrics-grid">
        {execution_assumptions_rows}
      </div>
    </section>
    {signal_metadata_rows}
    {data_quality_rows}
    <section class="section">
      <h2>Trade Return Semantics</h2>
      <p class="meta">Trade metrics are return-based. Win rate counts trades with trade_net_return &gt; 0.</p>
      <div class="metrics-grid">
        {trade_return_rows}
      </div>
    </section>
    <section class="section">
      <h2>Metrics Summary</h2>
      <div class="metrics-grid">
        {metrics_rows}
      </div>
    </section>
    <section class="section">
      <h2>Equity Curve</h2>
      {equity_figure_html}
    </section>
    <section class="section">
      <h2>Strategy vs Buy-and-Hold</h2>
      {strategy_benchmark_figure_html}
    </section>
    <section class="section">
      <h2>Drawdown</h2>
      {drawdown_figure_html}
    </section>
    <section class="section">
      <h2>Price with Trade Markers</h2>
      {price_trade_figure_html}
    </section>
  </main>
</body>
</html>
"""


def save_experiment_report(report_content: str, output_path: Path) -> Path:
    """Persist a rendered experiment report to disk."""
    # File export belongs here so storage.py can stay focused on raw experiment artifacts.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_content, encoding="utf-8")
    return output_path


def render_search_comparison_report(
    link_context: SearchReportLinkContext,
    ranked_results: list[ExperimentResult],
    artifact_receipts: list[ArtifactReceipt | None],
    top_equity_curves: dict[str, EquityCurveFrame],
    best_report_path: Path | None = None,
) -> str:
    """Assemble an HTML comparison report for ranked search results."""
    title = f"AlphaForge Search Report: {link_context.search_display_name}"
    execution_assumptions_rows = _build_execution_assumptions_rows(
        ranked_results[0].metadata if ranked_results else {}
    )
    signal_metadata_rows = _build_signal_metadata_rows(ranked_results[0].metadata if ranked_results else {})
    data_quality_rows = _build_data_quality_rows(ranked_results[0].metadata if ranked_results else {})
    trade_return_rows = _build_trade_return_rows()
    comparison_table = _build_search_comparison_table(
        link_context=link_context,
        ranked_results=ranked_results,
        artifact_receipts=artifact_receipts,
        best_report_path=best_report_path,
    )
    chart_sections = _build_search_chart_sections(top_equity_curves)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      background: #f7f7f7;
      color: #1f1f1f;
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    h1, h2 {{
      margin-bottom: 12px;
    }}
    .meta {{
      color: #555;
      margin-bottom: 24px;
    }}
    .section {{
      background: #ffffff;
      border: 1px solid #dddddd;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #e6e6e6;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #fafafa;
      font-weight: 600;
    }}
    code {{
      font-size: 0.9em;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(title)}</h1>
    <p class="meta">Link base: {escape(str(link_context.link_base_dir))}</p>
    <section class="section">
      <h2>Execution Assumptions</h2>
      <div class="metrics-grid">
        {execution_assumptions_rows}
      </div>
    </section>
    {signal_metadata_rows}
    {data_quality_rows}
    <section class="section">
      <h2>Trade Return Semantics</h2>
      <p class="meta">Trade metrics are return-based. Win rate counts trades with trade_net_return &gt; 0.</p>
      <div class="metrics-grid">
        {trade_return_rows}
      </div>
    </section>
    <section class="section">
      <h2>Ranked Comparison</h2>
      {comparison_table}
    </section>
    {chart_sections}
  </main>
</body>
</html>
"""


def _build_experiment_title(result: ExperimentResult) -> str:
    return f"AlphaForge Report: {result.strategy_spec.name} on {result.data_spec.symbol}"


def _build_search_comparison_table(
    link_context: SearchReportLinkContext,
    ranked_results: list[ExperimentResult],
    artifact_receipts: list[ArtifactReceipt | None],
    best_report_path: Path | None,
) -> str:
    if not ranked_results:
        return "<p>No ranked results available.</p>"
    if len(artifact_receipts) != len(ranked_results):
        raise ValueError("artifact_receipts must align one-to-one with ranked_results")

    parameter_names = list(ranked_results[0].strategy_spec.parameters)
    parameter_headers = [_titleize_parameter_name(name) for name in parameter_names]
    rows = []
    for rank, (result, receipt) in enumerate(zip(ranked_results, artifact_receipts, strict=False), start=1):
        parameters = result.strategy_spec.parameters
        artifact_path = _build_relative_artifact_path(link_context, receipt)
        best_report_link = _build_best_report_link(link_context, best_report_path, rank)
        parameter_cells = "".join(
            f"  <td>{escape(str(parameters.get(parameter_name, '')))}</td>\n" for parameter_name in parameter_names
        )
        rows.append(
            f"""<tr>
  <td>{rank}</td>
{parameter_cells}  <td>{escape(f"{result.score:.4f}")}</td>
  <td>{escape(_format_percent(result.metrics.total_return))}</td>
  <td>{escape(f"{result.metrics.sharpe_ratio:.2f}")}</td>
  <td>{escape(_format_percent(result.metrics.max_drawdown))}</td>
  <td>{escape(_format_percent(result.metrics.win_rate))}</td>
  <td>{escape(f"{result.metrics.turnover:.2f}")}</td>
  <td>{result.metrics.trade_count}</td>
  <td><code>{escape(artifact_path)}</code></td>
  <td>{best_report_link}</td>
</tr>"""
        )

    return f"""<table>
  <thead>
    <tr>
      <th>Rank</th>
      {"".join(f"<th>{escape(header)}</th>" for header in parameter_headers)}
      <th>Score</th>
      <th>Total Return</th>
      <th>Sharpe</th>
      <th>Max Drawdown</th>
      <th>Win Rate</th>
      <th>Turnover</th>
      <th>Trade Count</th>
      <th>Run Artifacts</th>
      <th>Best Report</th>
    </tr>
  </thead>
  <tbody>
    {"".join(rows)}
  </tbody>
</table>"""


def _build_search_chart_sections(top_equity_curves: dict[str, EquityCurveFrame]) -> str:
    if not top_equity_curves:
        return ""

    to_html = _load_plotly_to_html()
    equity_figure_html = _render_figure_html(
        to_html,
        build_equity_comparison_figure(top_equity_curves),
        include_plotlyjs=True,
    )
    drawdown_figure_html = _render_figure_html(
        to_html,
        build_drawdown_comparison_figure(top_equity_curves),
        include_plotlyjs=False,
    )
    return f"""<section class="section">
      <h2>Top Equity Curves</h2>
      {equity_figure_html}
    </section>
    <section class="section">
      <h2>Top Drawdowns</h2>
      {drawdown_figure_html}
    </section>"""


def _titleize_parameter_name(parameter_name: str) -> str:
    return parameter_name.replace("_", " ").title()


def _build_relative_artifact_path(
    link_context: SearchReportLinkContext,
    artifact_receipt: ArtifactReceipt | None,
) -> str:
    """Render a run-artifact path relative to the explicit report link base."""
    if artifact_receipt is None:
        return ""
    return str(artifact_receipt.run_dir.relative_to(link_context.link_base_dir))


def _build_best_report_link(
    link_context: SearchReportLinkContext,
    best_report_path: Path | None,
    rank: int,
) -> str:
    """Render the best-report link only from explicit presentation inputs."""
    if rank != 1 or best_report_path is None:
        return ""
    relative_path = best_report_path.relative_to(link_context.link_base_dir)
    href = escape(relative_path.as_posix())
    label = escape(str(relative_path))
    return f'<a href="{href}">{label}</a>'


def _build_metrics_rows(result: ExperimentResult, benchmark_summary: dict[str, float]) -> str:
    metrics = [
        ("Total Return", _format_percent(result.metrics.total_return)),
        ("Annualized Return", _format_percent(result.metrics.annualized_return)),
        ("Sharpe Ratio", f"{result.metrics.sharpe_ratio:.2f}"),
        ("Max Drawdown", _format_percent(result.metrics.max_drawdown)),
        ("Benchmark Return", _format_percent(benchmark_summary["total_return"])),
        ("Benchmark Max Drawdown", _format_percent(benchmark_summary["max_drawdown"])),
        ("Excess Return", _format_percent(result.metrics.total_return - benchmark_summary["total_return"])),
        ("Win Rate", _format_percent(result.metrics.win_rate)),
        ("Turnover", f"{result.metrics.turnover:.2f}"),
        ("Trade Count", str(result.metrics.trade_count)),
    ]
    cards = []
    for label, value in metrics:
        cards.append(
            f"""<div class="metric-card">
  <div class="metric-label">{escape(label)}</div>
  <div class="metric-value">{escape(value)}</div>
</div>"""
        )
    return "\n".join(cards)


def _build_execution_assumptions_rows(metadata: dict[str, object]) -> str:
    assumptions = build_execution_semantics_metadata()
    assumptions.update({key: metadata[key] for key in assumptions if key in metadata})
    cards = []
    labels = [
        ("Execution Semantics", assumptions["execution_semantics"]),
        ("Position Rule", assumptions["position_rule"]),
        ("Return Rule", assumptions["return_rule"]),
        ("Position Bounds", assumptions["position_bounds"]),
        ("Supports Shorting", assumptions["supports_shorting"]),
        ("Supports Leverage", assumptions["supports_leverage"]),
    ]
    for label, value in labels:
        cards.append(
            f"""<div class="metric-card">
  <div class="metric-label">{escape(label)}</div>
  <div class="metric-value">{escape(str(value))}</div>
</div>"""
        )
    return "\n".join(cards)


def _build_data_quality_rows(metadata: dict[str, object]) -> str:
    summary = metadata.get("data_quality_summary")
    if not isinstance(summary, dict):
        return ""
    cards = []
    labels = [
        ("Datetime Policy", summary.get("datetime_policy", "")),
        ("Duplicate Policy", summary.get("duplicate_datetime_policy", "")),
        ("Missing OHLC Policy", summary.get("missing_ohlc_policy", "")),
        ("Missing Volume Policy", summary.get("missing_volume_policy", "")),
        ("Source Rows", summary.get("source_row_count", "")),
        ("Accepted Rows", summary.get("accepted_row_count", "")),
        ("Volume Missing Rows", summary.get("volume_missing_row_count", "")),
    ]
    for label, value in labels:
        cards.append(
            f"""<div class="metric-card">
  <div class="metric-label">{escape(label)}</div>
  <div class="metric-value">{escape(str(value))}</div>
</div>"""
        )
    return f"""<section class="section">
      <h2>Market Data Quality</h2>
      <div class="metrics-grid">
        {"".join(cards)}
      </div>
    </section>"""


def _build_signal_metadata_rows(metadata: dict[str, object]) -> str:
    signal_keys = ("signal_file", "signal_name", "source", "symbol", "signal_row_count")
    if not any(key in metadata for key in signal_keys):
        return ""
    cards = []
    labels = [
        ("Signal File", metadata.get("signal_file", "")),
        ("Signal Name", metadata.get("signal_name", "")),
        ("Source", metadata.get("source", "")),
        ("Symbol", metadata.get("symbol", "")),
        ("Signal Row Count", metadata.get("signal_row_count", "")),
    ]
    for label, value in labels:
        cards.append(
            f"""<div class="metric-card">
  <div class="metric-label">{escape(label)}</div>
  <div class="metric-value">{escape(str(value))}</div>
</div>"""
        )
    return f"""<section class="section">
      <h2>Signal Metadata</h2>
      <div class="metrics-grid">
        {"".join(cards)}
      </div>
    </section>"""


def _build_trade_return_rows() -> str:
    cards = []
    labels = [
        ("Trade Log Schema", "entry_datetime / exit_datetime / entry_price / exit_price / holding_period / trade_gross_return / trade_net_return / cost_return_contribution / entry_target_position / exit_target_position"),
        ("Gross Return", "trade_gross_return"),
        ("Net Return", "trade_net_return"),
        ("Cost Contribution", "cost_return_contribution"),
        ("Win Rate Rule", "count(trade_net_return > 0) / trade_count"),
    ]
    for label, value in labels:
        cards.append(
            f"""<div class="metric-card">
  <div class="metric-label">{escape(label)}</div>
  <div class="metric-value">{escape(str(value))}</div>
</div>"""
        )
    return "\n".join(cards)


def _format_percent(value: float) -> str:
    return f"{value:.2%}"


def _render_figure_html(to_html, figure, include_plotlyjs: bool) -> str:
    return to_html(figure, full_html=False, include_plotlyjs=include_plotlyjs)


def _load_plotly_to_html():
    try:
        from plotly.io import to_html
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "plotly is required for AlphaForge report generation. Install project dependencies or add plotly to the environment."
        ) from exc
    return to_html
