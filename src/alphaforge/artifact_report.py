"""Local HTML report renderer for AlphaForge JSON/CSV backtest artifacts.

This module reads an artifact directory (or standalone OAP report JSON) and
produces a self-contained HTML file with charts and tables. No live trading,
broker execution, external data downloads, or ML training is performed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except Exception:  # pragma: no cover
    PLOTLY_AVAILABLE = False


_METRICS_SUMMARY = "metrics_summary.json"
_EQUITY_CURVE = "equity_curve.csv"
_TRADE_LOG = "trade_log.csv"
_RANKED_RESULTS = "ranked_results.csv"
_VALIDATION_SUMMARY = "validation_summary.json"
_WALK_FORWARD_SUMMARY = "walk_forward_summary.json"
_PERMUTATION_TEST_SUMMARY = "permutation_test_summary.json"


def render_artifact_report(
    artifact_dir: Path | str,
    *,
    output_path: Path | str | None = None,
    report_json_path: Path | str | None = None,
) -> str:
    """Render an HTML artifact report from an artifact directory.

    Parameters
    ----------
    artifact_dir : Path | str
        Directory containing AlphaForge backtest artifacts.
    output_path : Path | str | None
        Output HTML path. Defaults to ``<artifact_dir>/report.html``.
    report_json_path : Path | str | None
        Optional path to a standalone OAP report JSON (e.g. from
        ``alphaforge.oap_real_data_cli``). When provided, only the OAP section
        is rendered.

    Returns
    -------
    str
        Path to the generated HTML file.
    """
    artifact_dir = Path(artifact_dir)
    output_path = Path(output_path) if output_path else artifact_dir / "report.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metrics = None
    equity_curve = None
    trade_log = None
    ranked_results = None
    validation_summary = None
    walk_forward_summary = None
    permutation_summary = None
    oap_report = None

    if report_json_path:
        oap_report = _load_json(Path(report_json_path))
    else:
        metrics_path = artifact_dir / _METRICS_SUMMARY
        if metrics_path.exists():
            metrics = _load_json(metrics_path)

        equity_path = artifact_dir / _EQUITY_CURVE
        if equity_path.exists():
            equity_curve = pd.read_csv(equity_path, parse_dates=["datetime"])

        trade_log_path = artifact_dir / _TRADE_LOG
        if trade_log_path.exists():
            trade_log = pd.read_csv(trade_log_path)

        ranked_path = artifact_dir / _RANKED_RESULTS
        if ranked_path.exists():
            ranked_results = pd.read_csv(ranked_path)

        validation_path = artifact_dir / _VALIDATION_SUMMARY
        if validation_path.exists():
            validation_summary = _load_json(validation_path)

        wf_path = artifact_dir / _WALK_FORWARD_SUMMARY
        if wf_path.exists():
            walk_forward_summary = _load_json(wf_path)

        perm_path = artifact_dir / _PERMUTATION_TEST_SUMMARY
        if perm_path.exists():
            permutation_summary = _load_json(perm_path)

    html = _build_html(
        artifact_dir=str(artifact_dir),
        metrics=metrics,
        equity_curve=equity_curve,
        trade_log=trade_log,
        ranked_results=ranked_results,
        validation_summary=validation_summary,
        walk_forward_summary=walk_forward_summary,
        permutation_summary=permutation_summary,
        oap_report=oap_report,
    )
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_html(
    artifact_dir: str,
    metrics: dict[str, Any] | None,
    equity_curve: pd.DataFrame | None,
    trade_log: pd.DataFrame | None,
    ranked_results: pd.DataFrame | None,
    validation_summary: dict[str, Any] | None,
    walk_forward_summary: dict[str, Any] | None,
    permutation_summary: dict[str, Any] | None,
    oap_report: dict[str, Any] | None,
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = "OAP Real-Data Report" if oap_report else "AlphaForge Artifact Report"

    sections: list[str] = []
    sections.append(f"<h1>{title}</h1>")
    sections.append(f"<p>Generated: {timestamp}</p>")
    sections.append(f"<p>Artifact directory: <code>{artifact_dir}</code></p>")

    if oap_report:
        sections.append(_render_oap_report(oap_report))
    else:
        sections.append(_render_metrics(metrics))
        sections.append(_render_equity_chart(equity_curve))
        sections.append(_render_drawdown_chart(equity_curve))
        sections.append(_render_trade_log(trade_log))
        sections.append(_render_ranked_results(ranked_results))
        sections.append(_render_validation_summary(validation_summary))
        sections.append(_render_walk_forward_summary(walk_forward_summary))
        sections.append(_render_permutation_summary(permutation_summary))

    warnings = _collect_warnings(
        metrics, equity_curve, trade_log, ranked_results,
        validation_summary, walk_forward_summary, permutation_summary, oap_report,
    )

    body = "\n".join(sections)
    warning_block = ""
    if warnings:
        warning_block = "<div class='warnings'><h2>Warnings</h2><ul>" + "".join(
            f"<li>{w}</li>" for w in warnings
        ) + "</ul></div>"

    html = _HTML_TEMPLATE.format(
        title=title,
        body=body,
        warning_block=warning_block,
    )
    return html


def _render_metrics(metrics: dict[str, Any] | None) -> str:
    if metrics is None:
        return "<p class='missing'>metrics_summary.json not found.</p>"
    cards = []
    for key, value in metrics.items():
        label = key.replace("_", " ").title()
        val_str = f"{float(value):.4f}" if isinstance(value, (int, float)) else str(value)
        cards.append(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{val_str}</div></div>")
    return f"<h2>Metric Summary</h2><div class='metric-grid'>{''.join(cards)}</div>"


def _render_equity_chart(equity_curve: pd.DataFrame | None) -> str:
    if equity_curve is None or equity_curve.empty:
        return "<h2>Equity Curve</h2><p class='missing'>equity_curve.csv not found.</p>"
    if not PLOTLY_AVAILABLE:
        return "<h2>Equity Curve</h2><p class='missing'>Plotly is not available.</p>"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity_curve["datetime"],
        y=pd.to_numeric(equity_curve["equity"], errors="coerce").tolist(),
        mode="lines",
        name="Equity",
    ))
    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Date",
        yaxis_title="Equity",
        template="plotly_white",
    )
    return f"<h2>Equity Curve</h2>{fig.to_html(full_html=False, include_plotlyjs=False)}"


def _render_drawdown_chart(equity_curve: pd.DataFrame | None) -> str:
    if equity_curve is None or equity_curve.empty:
        return "<h2>Drawdown</h2><p class='missing'>equity_curve.csv not found.</p>"
    if "equity" not in equity_curve.columns:
        return "<h2>Drawdown</h2><p class='missing'>equity column not found.</p>"
    if not PLOTLY_AVAILABLE:
        return "<h2>Drawdown</h2><p class='missing'>Plotly is not available.</p>"
    equity_series = equity_curve["equity"]
    cummax = equity_series.cummax()
    if (cummax > 0).all() and cummax.iloc[-1] > 0:
        drawdown = equity_series / cummax - 1.0
    else:
        drawdown = equity_series - cummax
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity_curve["datetime"].astype(str).tolist(),
        y=drawdown.tolist(),
        mode="lines",
        name="Drawdown",
        fill="tozeroy",
        line=dict(color="red"),
    ))
    fig.update_layout(
        title="Drawdown",
        xaxis_title="Date",
        yaxis_title="Drawdown",
        template="plotly_white",
    )
    return f"<h2>Drawdown</h2>{fig.to_html(full_html=False, include_plotlyjs=False)}"


def _render_trade_log(trade_log: pd.DataFrame | None) -> str:
    if trade_log is None or trade_log.empty:
        return "<h2>Trade Log</h2><p class='missing'>trade_log.csv not found.</p>"
    preview = trade_log.head(20)
    table_html = preview.to_html(index=False, classes="data-table", border=1)
    return f"<h2>Trade Log</h2><p>Showing first {len(preview)} of {len(trade_log)} trades.</p>{table_html}"


def _render_ranked_results(ranked_results: pd.DataFrame | None) -> str:
    if ranked_results is None or ranked_results.empty:
        return "<h2>Ranked Results</h2><p class='missing'>ranked_results.csv not found.</p>"
    preview = ranked_results.head(20)
    table_html = preview.to_html(index=False, classes="data-table", border=1)
    return f"<h2>Ranked Results</h2><p>Showing first {len(preview)} of {len(ranked_results)} results.</p>{table_html}"


def _render_validation_summary(validation_summary: dict[str, Any] | None) -> str:
    if validation_summary is None:
        return "<h2>Validation Summary</h2><p class='missing'>validation_summary.json not found.</p>"
    return f"<h2>Validation Summary</h2><pre>{_json_pretty(validation_summary)}</pre>"


def _render_walk_forward_summary(walk_forward_summary: dict[str, Any] | None) -> str:
    if walk_forward_summary is None:
        return "<h2>Walk-Forward Summary</h2><p class='missing'>walk_forward_summary.json not found.</p>"
    return f"<h2>Walk-Forward Summary</h2><pre>{_json_pretty(walk_forward_summary)}</pre>"


def _render_permutation_summary(permutation_summary: dict[str, Any] | None) -> str:
    if permutation_summary is None:
        return "<h2>Permutation Test Summary</h2><p class='missing'>permutation_test_summary.json not found.</p>"
    return f"<h2>Permutation Test Summary</h2><pre>{_json_pretty(permutation_summary)}</pre>"


def _render_oap_report(oap_report: dict[str, Any]) -> str:
    return f"<h2>OAP Real-Data Report</h2><pre>{_json_pretty(oap_report)}</pre>"


def _json_pretty(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, default=str)


def _collect_warnings(
    metrics, equity_curve, trade_log, ranked_results,
    validation_summary, walk_forward_summary, permutation_summary, oap_report,
) -> list[str]:
    warnings = []
    if oap_report is None:
        if metrics is None:
            warnings.append("metrics_summary.json is missing.")
        if equity_curve is None:
            warnings.append("equity_curve.csv is missing; charts will not be rendered.")
        if trade_log is None:
            warnings.append("trade_log.csv is missing; trade table will not be rendered.")
        if ranked_results is None:
            warnings.append("ranked_results.csv is missing; ranked results table will not be rendered.")
        if validation_summary is None:
            warnings.append("validation_summary.json is missing.")
        if walk_forward_summary is None:
            warnings.append("walk_forward_summary.json is missing.")
        if permutation_summary is None:
            warnings.append("permutation_test_summary.json is missing.")
    return warnings


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
body {{ font-family: Arial, sans-serif; margin: 2em; background: #f9f9f9; }}
h1 {{ color: #222; }}
h2 {{ color: #444; margin-top: 1.5em; border-bottom: 1px solid #ccc; padding-bottom: 0.3em; }}
.metric-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1em; margin-top: 1em; }}
.metric-card {{ background: #fff; border: 1px solid #ddd; border-radius: 4px; padding: 1em; }}
.metric-label {{ font-size: 0.85em; color: #666; text-transform: uppercase; }}
.metric-value {{ font-size: 1.4em; font-weight: bold; color: #222; }}
.warnings {{ background: #fff3cd; border: 1px solid #ffeeba; border-radius: 4px; padding: 1em; margin-top: 2em; }}
.warnings h2 {{ border-bottom: none; margin-top: 0; }}
.missing {{ color: #888; font-style: italic; }}
.data-table {{ border-collapse: collapse; width: 100%; margin-top: 0.5em; }}
.data-table th {{ background: #eee; text-align: left; padding: 0.4em; }}
.data-table td {{ padding: 0.4em; }}
pre {{ background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; padding: 1em; overflow: auto; }}
</style>
</head>
<body>
{body}
{warning_block}
</body>
</html>
"""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Render AlphaForge artifact HTML report")
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report-json", type=Path, default=None)
    args = parser.parse_args()

    result = render_artifact_report(
        artifact_dir=args.artifact_dir,
        output_path=args.output,
        report_json_path=args.report_json,
    )
    print(f"Report written to: {result}")
