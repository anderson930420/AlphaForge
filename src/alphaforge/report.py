from __future__ import annotations

"""Report assembly and export interfaces for AlphaForge experiments.

This module is the single place for composing experiment outputs into a
shareable report artifact. It may orchestrate metrics, tables, and figures, but
it should not run backtests, compute metrics, or own figure construction.
"""

from html import escape
from pathlib import Path

import pandas as pd

from .schemas import EquityCurveFrame, ExperimentResult
from .visualization import (
    build_drawdown_comparison_figure,
    build_drawdown_figure,
    build_equity_comparison_figure,
    build_equity_curve_figure,
    build_price_trade_figure,
)


def render_experiment_report(
    result: ExperimentResult,
    equity_curve: EquityCurveFrame,
    trades: pd.DataFrame,
) -> str:
    """Assemble a single-experiment HTML report from existing artifacts."""
    to_html = _load_plotly_to_html()
    metrics_rows = _build_metrics_rows(result)
    equity_figure = build_equity_curve_figure(equity_curve)
    drawdown_figure = build_drawdown_figure(equity_curve)
    price_trade_figure = build_price_trade_figure(equity_curve, trades)
    equity_figure_html = _render_figure_html(to_html, equity_figure, include_plotlyjs=True)
    drawdown_figure_html = _render_figure_html(to_html, drawdown_figure, include_plotlyjs=False)
    price_trade_figure_html = _render_figure_html(to_html, price_trade_figure, include_plotlyjs=False)
    experiment_title = _build_experiment_title(result)

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
    <p class="meta">Strategy: {escape(result.strategy_spec.name)} | Symbol: {escape(result.data_spec.symbol)}</p>
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
    search_root: Path,
    ranked_results: list[ExperimentResult],
    top_equity_curves: dict[str, EquityCurveFrame],
    best_report_path: Path | None = None,
) -> str:
    """Assemble an HTML comparison report for ranked search results."""
    title = f"AlphaForge Search Report: {search_root.name}"
    comparison_table = _build_search_comparison_table(
        search_root=search_root,
        ranked_results=ranked_results,
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
    <p class="meta">Search root: {escape(str(search_root))}</p>
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
    search_root: Path,
    ranked_results: list[ExperimentResult],
    best_report_path: Path | None,
) -> str:
    if not ranked_results:
        return "<p>No ranked results available.</p>"

    rows = []
    for rank, result in enumerate(ranked_results, start=1):
        parameters = result.strategy_spec.parameters
        artifact_path = _build_relative_artifact_path(search_root, result)
        best_report_link = _build_best_report_link(search_root, best_report_path, rank)
        rows.append(
            f"""<tr>
  <td>{rank}</td>
  <td>{escape(str(parameters.get("short_window", "")))}</td>
  <td>{escape(str(parameters.get("long_window", "")))}</td>
  <td>{escape(f"{result.score:.4f}")}</td>
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
      <th>Short Window</th>
      <th>Long Window</th>
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


def _build_relative_artifact_path(search_root: Path, result: ExperimentResult) -> str:
    if result.equity_curve_path is None:
        return ""
    return str(result.equity_curve_path.parent.relative_to(search_root))


def _build_best_report_link(search_root: Path, best_report_path: Path | None, rank: int) -> str:
    if rank != 1 or best_report_path is None:
        return ""
    relative_path = best_report_path.relative_to(search_root)
    href = escape(relative_path.as_posix())
    label = escape(str(relative_path))
    return f'<a href="{href}">{label}</a>'


def _build_metrics_rows(result: ExperimentResult) -> str:
    metrics = [
        ("Total Return", _format_percent(result.metrics.total_return)),
        ("Annualized Return", _format_percent(result.metrics.annualized_return)),
        ("Sharpe Ratio", f"{result.metrics.sharpe_ratio:.2f}"),
        ("Max Drawdown", _format_percent(result.metrics.max_drawdown)),
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
