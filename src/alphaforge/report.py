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
from .visualization import build_drawdown_figure, build_equity_curve_figure


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
    equity_figure_html = to_html(equity_figure, full_html=False, include_plotlyjs="cdn")
    drawdown_figure_html = to_html(drawdown_figure, full_html=False, include_plotlyjs=False)
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


def _build_experiment_title(result: ExperimentResult) -> str:
    return f"AlphaForge Report: {result.strategy_spec.name} on {result.data_spec.symbol}"


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


def _load_plotly_to_html():
    try:
        from plotly.io import to_html
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "plotly is required for AlphaForge report generation. Install project dependencies or add plotly to the environment."
        ) from exc
    return to_html
