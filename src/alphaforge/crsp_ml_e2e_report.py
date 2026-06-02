"""CRSP ML E2E report artifact helpers.

This module reads the existing CRSP ML end-to-end artifacts and turns them into
report-ready summaries. It does not rerun the pipeline, change model behavior,
or add new feature engineering.
"""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .json_utils import json_safe_float, write_json_artifact
from .parquet_io import read_parquet_artifact


REPORT_TITLE = "CRSP ML E2E Report"
_PREVIEW_ROW_LIMIT = 10
_REQUIRED_JSON_FILENAMES = {
    "e2e_summary": Path("e2e_summary.json"),
    "dataset_qc": Path("dataset") / "crsp_ml_dataset_qc.json",
    "walkforward_qc": Path("walkforward") / "walk_forward_qc.json",
    "baseline_summary": Path("sklearn_baseline") / "summary.json",
    "window_metrics": Path("sklearn_baseline") / "window_metrics.json",
}
_OPTIONAL_PARQUET_FILENAME = Path("sklearn_baseline") / "prediction_portfolio_returns.parquet"
_MARKDOWN_SECTION_ORDER = [
    "Pipeline Overview",
    "Dataset",
    "Walk-Forward Splits",
    "Sklearn Baseline",
    "Prediction Portfolio",
    "Window Diagnostics",
    "Limitations",
    "Artifact Layout",
]


def load_crsp_ml_e2e_artifacts(e2e_dir: str | Path) -> dict[str, object]:
    """Load the CRSP ML E2E JSON artifacts and optional portfolio parquet."""
    e2e_path = Path(e2e_dir)
    if not e2e_path.exists():
        raise FileNotFoundError(f"CRSP ML E2E artifact directory does not exist: {e2e_path}")

    required_paths = {
        key: e2e_path / relative_path for key, relative_path in _REQUIRED_JSON_FILENAMES.items()
    }
    optional_portfolio_path = e2e_path / _OPTIONAL_PARQUET_FILENAME

    e2e_summary = _load_required_json(required_paths["e2e_summary"])
    dataset_qc = _load_required_json(required_paths["dataset_qc"])
    walkforward_qc = _load_required_json(required_paths["walkforward_qc"])
    baseline_summary = _load_required_json(required_paths["baseline_summary"])
    window_metrics = _load_required_json(required_paths["window_metrics"])

    portfolio_returns = None
    if optional_portfolio_path.exists():
        portfolio_returns = read_parquet_artifact(optional_portfolio_path)

    artifact_paths = {
        "e2e_dir": str(e2e_path),
        "e2e_summary": str(required_paths["e2e_summary"]),
        "dataset_qc": str(required_paths["dataset_qc"]),
        "walkforward_qc": str(required_paths["walkforward_qc"]),
        "baseline_summary": str(required_paths["baseline_summary"]),
        "window_metrics": str(required_paths["window_metrics"]),
        "portfolio_returns": str(optional_portfolio_path),
    }

    return {
        "e2e_dir": e2e_path,
        "artifact_paths": artifact_paths,
        "e2e_summary": e2e_summary,
        "dataset_qc": dataset_qc,
        "walkforward_qc": walkforward_qc,
        "baseline_summary": baseline_summary,
        "window_metrics": window_metrics,
        "portfolio_returns": portfolio_returns,
    }


def build_crsp_ml_e2e_report_payload(artifacts: dict[str, object]) -> dict[str, object]:
    """Build a report payload from already-loaded CRSP ML E2E artifacts."""
    e2e_summary = _require_mapping(artifacts, "e2e_summary")
    dataset_qc = _require_mapping(artifacts, "dataset_qc")
    walkforward_qc = _require_mapping(artifacts, "walkforward_qc")
    baseline_summary = _require_mapping(artifacts, "baseline_summary")
    window_metrics_artifact = _require_mapping(artifacts, "window_metrics")
    portfolio_returns = artifacts.get("portfolio_returns")
    artifact_paths = dict(artifacts.get("artifact_paths", {}))
    window_metrics_summary = _build_window_metrics_summary(window_metrics_artifact)
    portfolio_summary = _build_portfolio_summary(
        baseline_summary=baseline_summary,
        portfolio_returns=portfolio_returns,
    )

    report = {
        "title": REPORT_TITLE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_summary": _build_pipeline_summary(
            e2e_summary=e2e_summary,
            baseline_summary=baseline_summary,
        ),
        "dataset_summary": _build_dataset_summary(dataset_qc=dataset_qc),
        "walkforward_summary": _build_walkforward_summary(
            e2e_summary=e2e_summary,
            walkforward_qc=walkforward_qc,
        ),
        "model_summary": _build_model_summary(baseline_summary=baseline_summary),
        "window_metrics_summary": window_metrics_summary,
        "portfolio_summary": portfolio_summary,
        "visual_summary": _build_visual_summary(
            window_metrics_artifact=window_metrics_artifact,
            window_metrics_summary=window_metrics_summary,
            portfolio_returns=portfolio_returns,
        ),
        "limitations": [
            "No transaction costs modeled in this report's portfolio metrics",
            "No hyperparameter tuning in this report's baseline",
            "No feature neutralization in this report",
            "No Compustat fundamentals in this report's feature set",
            "Cross-sectional preprocessing, PyTorch baselines, and dashboard views are implemented in separate AlphaForge components and are not summarized in this E2E report",
            "This report is a presentation layer only; it does not rerun the pipeline",
        ],
        "artifact_paths": artifact_paths,
    }
    return _normalize_json_value(report)


def render_crsp_ml_e2e_report_markdown(report: dict[str, object]) -> str:
    """Render a readable markdown report from the CRSP ML E2E payload."""
    lines: list[str] = [
        f"# {report.get('title', REPORT_TITLE)}",
        "",
        f"Generated at: `{_format_text(report.get('generated_at'))}`",
        "",
        "This report is derived from existing CRSP ML E2E artifacts. It does not rerun the pipeline or change model behavior.",
        "",
    ]

    lines.extend(
        [
            "## Pipeline Overview",
            _render_markdown_kv_table(
                report.get("pipeline_summary", {}),
                [
                    "monthly_input",
                    "output_dir",
                    "dataset_rows",
                    "dataset_assets",
                    "dataset_date_min",
                    "dataset_date_max",
                    "walkforward_windows",
                    "model_name",
                    "prediction_rows",
                    "prediction_date_min",
                    "prediction_date_max",
                ],
            ),
            "",
            "## Dataset",
            _render_markdown_kv_table(
                report.get("dataset_summary", {}),
                [
                    "rows",
                    "assets",
                    "months",
                    "date_min",
                    "date_max",
                    "missing_label_ratio",
                    "duplicate_asset_date_rows",
                ],
            ),
            "",
            "## Walk-Forward Splits",
            _render_markdown_kv_table(
                report.get("walkforward_summary", {}),
                [
                    "windows",
                    "first_window_id",
                    "last_window_id",
                    "total_train_rows",
                    "total_test_rows",
                    "first_train_start",
                    "last_test_end",
                ],
            ),
            "",
            "## Sklearn Baseline",
            _render_markdown_kv_table(
                report.get("model_summary", {}),
                [
                    "model_name",
                    "label_col",
                    "quantile",
                    "random_state",
                    "prediction_rows",
                    "average_mse",
                    "average_mae",
                    "average_prediction_ic",
                    "average_prediction_rank_ic",
                ],
            ),
            "",
            "## Prediction Portfolio",
            _render_markdown_kv_table(
                report.get("portfolio_summary", {}),
                [
                    "rows",
                    "date_min",
                    "date_max",
                    "cumulative_return",
                    "annualized_return",
                    "annualized_volatility",
                    "sharpe",
                    "mean_monthly_return",
                    "std_monthly_return",
                    "positive_month_ratio",
                    "best_month",
                    "worst_month",
                ],
            ),
        ]
    )

    portfolio_preview = report.get("portfolio_summary", {}).get("cumulative_return_preview", [])
    if portfolio_preview:
        lines.extend(
            [
                "",
                "### Cumulative Return Preview",
                _render_markdown_records_table(
                    portfolio_preview,
                    ["date", "long_short_ret", "cumulative_return"],
                ),
            ]
        )

    window_summary = report.get("window_metrics_summary", {})
    lines.extend(
        [
            "",
            "## Window Diagnostics",
            _render_markdown_kv_table(
                window_summary,
                [
                    "window_count",
                    "positive_prediction_ic_windows",
                    "positive_prediction_rank_ic_windows",
                    "mean_prediction_ic",
                    "median_prediction_ic",
                    "mean_prediction_rank_ic",
                    "median_prediction_rank_ic",
                ],
            ),
        ]
    )

    if window_summary.get("best_prediction_ic_window") or window_summary.get("worst_prediction_ic_window"):
        lines.extend(
            [
                "",
                "### Best and Worst Windows",
                _render_markdown_records_table(
                    [
                        _flatten_window_metric_entry(
                            "best_prediction_ic_window",
                            window_summary.get("best_prediction_ic_window"),
                        ),
                        _flatten_window_metric_entry(
                            "worst_prediction_ic_window",
                            window_summary.get("worst_prediction_ic_window"),
                        ),
                        _flatten_window_metric_entry(
                            "best_prediction_rank_ic_window",
                            window_summary.get("best_prediction_rank_ic_window"),
                        ),
                        _flatten_window_metric_entry(
                            "worst_prediction_rank_ic_window",
                            window_summary.get("worst_prediction_rank_ic_window"),
                        ),
                    ],
                    ["window_type", "window_id", "prediction_ic", "prediction_rank_ic", "mse", "mae"],
                ),
            ]
        )

    preview_rows = window_summary.get("window_metrics_preview", [])
    if preview_rows:
        preview_note = window_summary.get("window_metrics_preview_note")
        lines.extend(["", "### Window Metrics Preview"])
        if preview_note:
            lines.extend([preview_note, ""])
        lines.append(
            _render_markdown_records_table(
                preview_rows,
                [
                    "window_id",
                    "train_rows",
                    "test_rows",
                    "mse",
                    "mae",
                    "prediction_ic",
                    "prediction_rank_ic",
                ],
            )
        )

    lines.extend(
        [
            "",
            "## Limitations",
            _render_markdown_bullets(report.get("limitations", [])),
            "",
            "## Artifact Layout",
            _render_markdown_kv_table(
                report.get("artifact_paths", {}),
                list(report.get("artifact_paths", {}).keys()),
            ),
        ]
    )

    return "\n".join(lines).strip() + "\n"


def render_crsp_ml_e2e_report_html(report: dict[str, object]) -> str:
    """Render a deterministic static HTML report from the CRSP ML E2E payload."""
    title = _format_text(report.get("title", REPORT_TITLE))
    generated_at = _format_text(report.get("generated_at"))
    pipeline_summary = report.get("pipeline_summary", {})
    dataset_summary = report.get("dataset_summary", {})
    walkforward_summary = report.get("walkforward_summary", {})
    model_summary = report.get("model_summary", {})
    portfolio_summary = report.get("portfolio_summary", {})
    window_summary = report.get("window_metrics_summary", {})
    visual_summary = report.get("visual_summary", {})
    artifact_paths = report.get("artifact_paths", {})
    limitations = report.get("limitations", [])

    sections = [
        _html_section(
            "Pipeline Overview",
            _html_kv_table(
                pipeline_summary,
                [
                    "monthly_input",
                    "output_dir",
                    "dataset_rows",
                    "dataset_assets",
                    "dataset_date_min",
                    "dataset_date_max",
                    "walkforward_windows",
                    "model_name",
                    "prediction_rows",
                    "prediction_date_min",
                    "prediction_date_max",
                ],
            ),
        ),
        _html_section(
            "Dataset",
            _html_kv_table(
                dataset_summary,
                [
                    "rows",
                    "assets",
                    "months",
                    "date_min",
                    "date_max",
                    "missing_label_ratio",
                    "duplicate_asset_date_rows",
                ],
            ),
        ),
        _html_section(
            "Walk-Forward Splits",
            _html_kv_table(
                walkforward_summary,
                [
                    "windows",
                    "first_window_id",
                    "last_window_id",
                    "total_train_rows",
                    "total_test_rows",
                    "first_train_start",
                    "last_test_end",
                ],
            ),
        ),
        _html_section(
            "Sklearn Baseline",
            _html_kv_table(
                model_summary,
                [
                    "model_name",
                    "label_col",
                    "quantile",
                    "random_state",
                    "prediction_rows",
                    "average_mse",
                    "average_mae",
                    "average_prediction_ic",
                    "average_prediction_rank_ic",
                ],
            ),
        ),
        _html_visual_summary_section(
            window_summary=window_summary,
            portfolio_summary=portfolio_summary,
            visual_summary=visual_summary,
        ),
        _html_section(
            "Prediction Portfolio",
            _html_kv_table(
                portfolio_summary,
                [
                    "rows",
                    "date_min",
                    "date_max",
                    "cumulative_return",
                    "annualized_return",
                    "annualized_volatility",
                    "sharpe",
                    "mean_monthly_return",
                    "std_monthly_return",
                    "positive_month_ratio",
                    "best_month",
                    "worst_month",
                ],
            )
            + _html_optional_preview_section(
                "Cumulative Return Preview",
                portfolio_summary.get("cumulative_return_preview", []),
                ["date", "long_short_ret", "cumulative_return"],
            ),
        ),
        _html_section(
            "Window Diagnostics",
            _html_kv_table(
                window_summary,
                [
                    "window_count",
                    "positive_prediction_ic_windows",
                    "positive_prediction_rank_ic_windows",
                    "mean_prediction_ic",
                    "median_prediction_ic",
                    "mean_prediction_rank_ic",
                    "median_prediction_rank_ic",
                ],
            )
            + _html_optional_window_extrema_section(window_summary),
        ),
        _html_section("Limitations", _html_bullet_list(limitations)),
        _html_section(
            "Artifact Layout",
            _html_kv_table(artifact_paths, list(artifact_paths.keys())),
        ),
    ]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f7fb;
      --panel: #ffffff;
      --text: #1c2430;
      --muted: #5d6878;
      --line: #d7dfea;
      --accent: #2457a6;
      --accent-soft: #eef3fb;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top right, rgba(36, 87, 166, 0.08), transparent 28%),
        linear-gradient(180deg, #f8fbff 0%, var(--bg) 100%);
      color: var(--text);
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }}
    .hero {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 24px 24px 20px;
      box-shadow: 0 12px 28px rgba(20, 36, 72, 0.06);
      margin-bottom: 20px;
    }}
    .hero h1 {{
      margin: 0 0 10px;
      font-size: 2rem;
      line-height: 1.15;
    }}
    .hero p {{
      margin: 8px 0 0;
      color: var(--muted);
    }}
    .section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 20px;
      margin: 18px 0;
      box-shadow: 0 10px 24px rgba(20, 36, 72, 0.04);
    }}
    .section h2 {{
      margin: 0 0 14px;
      font-size: 1.2rem;
    }}
    .subsection {{
      margin-top: 18px;
    }}
    .subsection h3 {{
      margin: 0 0 10px;
      font-size: 1rem;
      color: var(--text);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 8px 10px;
      vertical-align: top;
      text-align: left;
      word-break: break-word;
    }}
    th {{
      background: var(--accent-soft);
      color: var(--text);
      font-weight: 600;
    }}
    tbody tr:last-child td {{
      border-bottom: none;
    }}
    code, pre {{
      background: #f6f8fc;
      border-radius: 8px;
      padding: 0.12rem 0.35rem;
    }}
    pre {{
      padding: 12px 14px;
      overflow-x: auto;
      white-space: pre-wrap;
      border: 1px solid var(--line);
    }}
    ul {{
      margin: 0;
      padding-left: 20px;
    }}
    li + li {{
      margin-top: 6px;
    }}
    .meta {{
      color: var(--muted);
      margin-top: 6px;
    }}
    .note {{
      margin: 0 0 12px;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .visual-summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}
    .visual-card {{
      border: 1px solid var(--line);
      border-radius: 14px;
      background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
      padding: 14px 16px;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
    }}
    .visual-card-label {{
      color: var(--muted);
      font-size: 0.82rem;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      margin-bottom: 6px;
    }}
    .visual-card-value {{
      font-size: 1.55rem;
      font-weight: 700;
      line-height: 1.1;
      color: var(--text);
      word-break: break-word;
    }}
    .visual-charts {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
    }}
    .visual-chart {{
      border: 1px solid var(--line);
      border-radius: 16px;
      background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
      padding: 16px;
    }}
    .visual-chart h3 {{
      margin: 0 0 10px;
      font-size: 1rem;
    }}
    .svg-scroll {{
      overflow-x: auto;
      padding-bottom: 4px;
    }}
    .svg-scroll svg {{
      display: block;
    }}
    .chart-caption {{
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 0.94rem;
      line-height: 1.45;
    }}
    .chart-legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin: 0 0 10px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .chart-legend span {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .legend-swatch {{
      width: 12px;
      height: 12px;
      border-radius: 999px;
      display: inline-block;
      border: 1px solid transparent;
    }}
    .legend-positive {{
      background: #1f8a54;
    }}
    .legend-negative {{
      background: #c63d4f;
    }}
    .legend-best {{
      background: #2457a6;
      border-color: #0f172a;
    }}
    .legend-worst {{
      background: #c63d4f;
      border-color: #0f172a;
      border-style: dashed;
    }}
  </style>
</head>
<body>
  <main>
    <header class="hero">
      <h1>{escape(title)}</h1>
      <p>Generated at <code>{escape(generated_at)}</code></p>
      <p class="meta">This report is derived from existing CRSP ML E2E artifacts. It does not rerun the pipeline or change model behavior.</p>
    </header>
    {''.join(sections)}
  </main>
</body>
</html>
"""
    return html


def write_crsp_ml_e2e_report(
    e2e_dir: str | Path,
    output_dir: str | Path,
    *,
    write_html: bool = True,
) -> dict[str, object]:
    """Write the CRSP ML E2E report artifacts and return the report payload."""
    artifacts = load_crsp_ml_e2e_artifacts(e2e_dir)
    report = build_crsp_ml_e2e_report_payload(artifacts)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    report_json_path = output_path / "report.json"
    report_md_path = output_path / "report.md"
    report_html_path = output_path / "report.html"

    artifact_paths = dict(report.get("artifact_paths", {}))
    artifact_paths.update(
        {
            "report_dir": str(output_path),
            "report_json": str(report_json_path),
            "report_md": str(report_md_path),
            "report_html": str(report_html_path) if write_html else None,
        }
    )
    report["artifact_paths"] = artifact_paths
    report = _normalize_json_value(report)

    report_md = render_crsp_ml_e2e_report_markdown(report)
    report_md_path.write_text(report_md, encoding="utf-8")

    if write_html:
        report_html = render_crsp_ml_e2e_report_html(report)
        report_html_path.write_text(report_html, encoding="utf-8")

    write_json_artifact(report_json_path, report)
    return report


def _load_required_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required CRSP ML E2E artifact is missing: {path}")
    return _load_json(path)


def _load_json(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _require_mapping(artifacts: dict[str, object], key: str) -> dict[str, Any]:
    value = artifacts.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"{key} must be a dictionary of loaded CRSP ML E2E artifacts")
    return value


def _build_pipeline_summary(
    *,
    e2e_summary: dict[str, Any],
    baseline_summary: dict[str, Any],
) -> dict[str, object]:
    return {
        "monthly_input": e2e_summary.get("monthly_input"),
        "output_dir": e2e_summary.get("output_dir"),
        "dataset_rows": e2e_summary.get("dataset_rows"),
        "dataset_assets": e2e_summary.get("dataset_assets"),
        "dataset_date_min": e2e_summary.get("dataset_date_min"),
        "dataset_date_max": e2e_summary.get("dataset_date_max"),
        "walkforward_windows": e2e_summary.get("walkforward_windows"),
        "model_name": e2e_summary.get("model_name") or baseline_summary.get("model_name"),
        "prediction_rows": e2e_summary.get("prediction_rows"),
        "prediction_date_min": e2e_summary.get("prediction_date_min") or baseline_summary.get("date_min"),
        "prediction_date_max": e2e_summary.get("prediction_date_max") or baseline_summary.get("date_max"),
        "train_years": e2e_summary.get("train_years"),
        "test_years": e2e_summary.get("test_years"),
        "step_years": e2e_summary.get("step_years"),
        "quantile": e2e_summary.get("quantile"),
        "random_state": e2e_summary.get("random_state"),
    }


def _build_dataset_summary(*, dataset_qc: dict[str, Any]) -> dict[str, object]:
    return {
        "rows": dataset_qc.get("rows"),
        "assets": dataset_qc.get("assets"),
        "months": dataset_qc.get("months"),
        "date_min": dataset_qc.get("date_min"),
        "date_max": dataset_qc.get("date_max"),
        "missing_label_ratio": dataset_qc.get("missing_label_ratio"),
        "duplicate_asset_date_rows": dataset_qc.get("duplicate_asset_date_rows"),
        "feature_columns": dataset_qc.get("feature_columns"),
        "label_column": dataset_qc.get("label_column"),
        "frequency": dataset_qc.get("frequency"),
    }


def _build_walkforward_summary(
    *,
    e2e_summary: dict[str, Any],
    walkforward_qc: dict[str, Any],
) -> dict[str, object]:
    return {
        "windows": walkforward_qc.get("windows"),
        "first_window_id": e2e_summary.get("first_window_id"),
        "last_window_id": e2e_summary.get("last_window_id"),
        "total_train_rows": walkforward_qc.get("total_train_rows"),
        "total_test_rows": walkforward_qc.get("total_test_rows"),
        "first_train_start": walkforward_qc.get("first_train_start"),
        "last_test_end": walkforward_qc.get("last_test_end"),
        "train_years": walkforward_qc.get("train_years"),
        "test_years": walkforward_qc.get("test_years"),
        "step_years": walkforward_qc.get("step_years"),
    }


def _build_model_summary(*, baseline_summary: dict[str, Any]) -> dict[str, object]:
    return {
        "model_name": baseline_summary.get("model_name"),
        "label_col": baseline_summary.get("label_col"),
        "feature_cols": baseline_summary.get("feature_cols"),
        "quantile": baseline_summary.get("quantile"),
        "random_state": baseline_summary.get("random_state"),
        "prediction_rows": baseline_summary.get("prediction_rows"),
        "date_min": baseline_summary.get("date_min"),
        "date_max": baseline_summary.get("date_max"),
        "average_mse": baseline_summary.get("average_mse"),
        "average_mae": baseline_summary.get("average_mae"),
        "average_prediction_ic": baseline_summary.get("average_prediction_ic"),
        "average_prediction_rank_ic": baseline_summary.get("average_prediction_rank_ic"),
    }


def _build_window_metrics_summary(window_metrics_artifact: dict[str, Any]) -> dict[str, object]:
    window_metrics = window_metrics_artifact.get("window_metrics", [])
    if not isinstance(window_metrics, list):
        raise TypeError("window_metrics artifact must contain a list under 'window_metrics'")

    frame = pd.DataFrame(window_metrics)
    summary = {
        "window_count": int(len(frame)),
        "positive_prediction_ic_windows": 0,
        "positive_prediction_rank_ic_windows": 0,
        "mean_prediction_ic": None,
        "median_prediction_ic": None,
        "mean_prediction_rank_ic": None,
        "median_prediction_rank_ic": None,
        "best_prediction_ic_window": None,
        "worst_prediction_ic_window": None,
        "best_prediction_rank_ic_window": None,
        "worst_prediction_rank_ic_window": None,
        "window_metrics_preview": [],
        "window_metrics_preview_note": None,
    }
    if frame.empty:
        return summary

    frame = frame.copy()
    for column in ["prediction_ic", "prediction_rank_ic", "mse", "mae"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    summary["positive_prediction_ic_windows"] = int(frame["prediction_ic"].gt(0).sum()) if "prediction_ic" in frame.columns else 0
    summary["positive_prediction_rank_ic_windows"] = (
        int(frame["prediction_rank_ic"].gt(0).sum()) if "prediction_rank_ic" in frame.columns else 0
    )
    summary["mean_prediction_ic"] = _mean_or_none(frame.get("prediction_ic"))
    summary["median_prediction_ic"] = _median_or_none(frame.get("prediction_ic"))
    summary["mean_prediction_rank_ic"] = _mean_or_none(frame.get("prediction_rank_ic"))
    summary["median_prediction_rank_ic"] = _median_or_none(frame.get("prediction_rank_ic"))

    summary["best_prediction_ic_window"] = _window_metric_snapshot(
        frame, metric_column="prediction_ic", extremum="max"
    )
    summary["worst_prediction_ic_window"] = _window_metric_snapshot(
        frame, metric_column="prediction_ic", extremum="min"
    )
    summary["best_prediction_rank_ic_window"] = _window_metric_snapshot(
        frame, metric_column="prediction_rank_ic", extremum="max"
    )
    summary["worst_prediction_rank_ic_window"] = _window_metric_snapshot(
        frame, metric_column="prediction_rank_ic", extremum="min"
    )

    preview_rows, truncated = _compact_records(frame, preview_limit=_PREVIEW_ROW_LIMIT)
    summary["window_metrics_preview"] = [
        _window_metric_preview_row(row) for row in preview_rows
    ]
    if truncated:
        summary["window_metrics_preview_note"] = (
            f"Showing the first and last {min(_PREVIEW_ROW_LIMIT // 2, len(frame))} rows of {len(frame)} windows."
        )
    return summary


def _build_portfolio_summary(
    *,
    baseline_summary: dict[str, Any],
    portfolio_returns: object,
) -> dict[str, object]:
    summary = {
        "rows": baseline_summary.get("portfolio_rows"),
        "date_min": baseline_summary.get("portfolio_date_min"),
        "date_max": baseline_summary.get("portfolio_date_max"),
        "cumulative_return": baseline_summary.get("cumulative_return"),
        "annualized_return": baseline_summary.get("annualized_return"),
        "annualized_volatility": baseline_summary.get("annualized_volatility"),
        "sharpe": baseline_summary.get("sharpe"),
        "mean_monthly_return": baseline_summary.get("mean_monthly_return"),
        "std_monthly_return": baseline_summary.get("std_monthly_return"),
        "positive_month_ratio": baseline_summary.get("positive_month_ratio"),
        "worst_month": baseline_summary.get("worst_month"),
        "best_month": baseline_summary.get("best_month"),
        "cumulative_return_preview": [],
        "cumulative_return_preview_note": None,
    }

    if not isinstance(portfolio_returns, pd.DataFrame) or portfolio_returns.empty:
        return summary

    preview_rows, truncated = _compact_portfolio_records(portfolio_returns, preview_limit=_PREVIEW_ROW_LIMIT)
    summary["cumulative_return_preview"] = preview_rows
    if truncated:
        summary["cumulative_return_preview_note"] = (
            f"Showing the first and last {min(_PREVIEW_ROW_LIMIT // 2, len(portfolio_returns))} months of {len(portfolio_returns)} portfolio rows."
        )
    return summary


def _build_visual_summary(
    *,
    window_metrics_artifact: dict[str, Any],
    window_metrics_summary: dict[str, object],
    portfolio_returns: object,
) -> dict[str, object]:
    window_metrics = window_metrics_artifact.get("window_metrics", [])
    if not isinstance(window_metrics, list):
        raise TypeError("window_metrics artifact must contain a list under 'window_metrics'")

    best_prediction_rank_ic_window = window_metrics_summary.get("best_prediction_rank_ic_window") or {}
    worst_prediction_rank_ic_window = window_metrics_summary.get("worst_prediction_rank_ic_window") or {}
    best_window_id = best_prediction_rank_ic_window.get("window_id")
    worst_window_id = worst_prediction_rank_ic_window.get("window_id")

    rank_ic_windows: list[dict[str, object]] = []
    for row in window_metrics:
        if not isinstance(row, dict):
            continue
        window_id = row.get("window_id")
        rank_ic_windows.append(
            {
                "window_id": window_id,
                "prediction_rank_ic": _safe_float(row.get("prediction_rank_ic")),
                "is_best": window_id is not None and window_id == best_window_id,
                "is_worst": window_id is not None and window_id == worst_window_id,
            }
        )

    portfolio_cumulative_return_points = _build_portfolio_cumulative_return_points(portfolio_returns)
    return {
        "rank_ic_windows": rank_ic_windows,
        "portfolio_cumulative_return_points": portfolio_cumulative_return_points,
        "portfolio_final_cumulative_return": (
            _safe_float(portfolio_cumulative_return_points[-1]["cumulative_return"])
            if portfolio_cumulative_return_points
            else None
        ),
    }


def _compact_records(
    frame: pd.DataFrame,
    *,
    preview_limit: int,
) -> tuple[list[dict[str, object]], bool]:
    if frame.empty:
        return [], False

    records = frame.to_dict(orient="records")
    if len(records) <= preview_limit:
        return records, False

    head_count = preview_limit // 2
    tail_count = preview_limit - head_count
    preview = records[:head_count] + records[-tail_count:]
    return preview, True


def _compact_portfolio_records(
    portfolio_returns: pd.DataFrame,
    *,
    preview_limit: int,
) -> tuple[list[dict[str, object]], bool]:
    records = _build_portfolio_cumulative_return_points(portfolio_returns)
    if not records:
        return [], False

    if len(records) <= preview_limit:
        return records, False

    head_count = preview_limit // 2
    tail_count = preview_limit - head_count
    preview = records[:head_count] + records[-tail_count:]
    return preview, True


def _build_portfolio_cumulative_return_points(portfolio_returns: object) -> list[dict[str, object]]:
    if not isinstance(portfolio_returns, pd.DataFrame) or portfolio_returns.empty:
        return []

    required_columns = {"date", "long_short_ret"}
    missing = required_columns - set(portfolio_returns.columns)
    if missing:
        raise ValueError(f"portfolio_returns parquet is missing required columns: {sorted(missing)}")

    frame = portfolio_returns.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if frame["date"].isna().any():
        raise ValueError("portfolio_returns parquet contains unparseable dates")
    frame["long_short_ret"] = pd.to_numeric(frame["long_short_ret"], errors="coerce")
    frame = frame.loc[frame["long_short_ret"].notna()].copy()
    if frame.empty:
        return []

    frame = frame.sort_values("date", kind="mergesort").reset_index(drop=True)
    frame["cumulative_return"] = (1.0 + frame["long_short_ret"]).cumprod() - 1.0
    frame["date"] = frame["date"].dt.date.astype(str)

    points: list[dict[str, object]] = []
    for row in frame[["date", "long_short_ret", "cumulative_return"]].to_dict(orient="records"):
        points.append(
            {
                "date": row["date"],
                "long_short_ret": _safe_float(row["long_short_ret"]),
                "cumulative_return": _safe_float(row["cumulative_return"]),
            }
        )
    return points


def _window_metric_snapshot(
    frame: pd.DataFrame,
    *,
    metric_column: str,
    extremum: str,
) -> dict[str, object] | None:
    if metric_column not in frame.columns:
        return None

    metric_series = frame[metric_column]
    metric_series = metric_series.dropna()
    if metric_series.empty:
        return None

    index = metric_series.idxmax() if extremum == "max" else metric_series.idxmin()
    row = frame.loc[index]
    return _flatten_window_metric_row(row)


def _window_metric_preview_row(row: dict[str, object]) -> dict[str, object]:
    return {
        "window_id": row.get("window_id"),
        "train_rows": row.get("train_rows"),
        "test_rows": row.get("test_rows"),
        "mse": row.get("mse"),
        "mae": row.get("mae"),
        "prediction_ic": row.get("prediction_ic"),
        "prediction_rank_ic": row.get("prediction_rank_ic"),
    }


def _flatten_window_metric_entry(window_type: str, entry: dict[str, object] | None) -> dict[str, object]:
    if entry is None:
        return {
            "window_type": window_type,
            "window_id": None,
            "prediction_ic": None,
            "prediction_rank_ic": None,
            "mse": None,
            "mae": None,
        }
    return {
        "window_type": window_type,
        "window_id": entry.get("window_id"),
        "prediction_ic": entry.get("prediction_ic"),
        "prediction_rank_ic": entry.get("prediction_rank_ic"),
        "mse": entry.get("mse"),
        "mae": entry.get("mae"),
    }


def _flatten_window_metric_row(row: pd.Series) -> dict[str, object]:
    return {
        "window_id": row.get("window_id"),
        "prediction_ic": row.get("prediction_ic"),
        "prediction_rank_ic": row.get("prediction_rank_ic"),
        "mse": row.get("mse"),
        "mae": row.get("mae"),
        "train_rows": row.get("train_rows"),
        "test_rows": row.get("test_rows"),
        "train_date_min": row.get("train_date_min"),
        "train_date_max": row.get("train_date_max"),
        "test_date_min": row.get("test_date_min"),
        "test_date_max": row.get("test_date_max"),
    }


def _mean_or_none(values: pd.Series | None) -> float | None:
    if values is None:
        return None
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    return json_safe_float(float(numeric.mean()))


def _median_or_none(values: pd.Series | None) -> float | None:
    if values is None:
        return None
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    return json_safe_float(float(numeric.median()))


def _render_markdown_kv_table(mapping: dict[str, object], keys: list[str]) -> str:
    rows = []
    for key in keys:
        rows.append((key, _format_text(mapping.get(key))))
    return _markdown_table(["Field", "Value"], rows)


def _render_markdown_records_table(records: list[dict[str, object]], keys: list[str]) -> str:
    rows = []
    for record in records:
        rows.append(tuple(_format_text(record.get(key)) for key in keys))
    return _markdown_table([_title_case(key) for key in keys], rows)


def _render_markdown_bullets(items: list[object]) -> str:
    if not items:
        return "- n/a"
    return "\n".join(f"- {_format_text(item)}" for item in items)


def _markdown_table(headers: list[str], rows: list[tuple[str, ...]]) -> str:
    if not rows:
        rows = [tuple("n/a" for _ in headers)]

    header_line = "| " + " | ".join(_escape_markdown_cell(header) for header in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body_lines = []
    for row in rows:
        body_lines.append("| " + " | ".join(_escape_markdown_cell(cell) for cell in row) + " |")
    return "\n".join([header_line, separator, *body_lines])


def _escape_markdown_cell(value: object) -> str:
    text = _format_text(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def _html_section(title: str, body: str) -> str:
    return f'<section class="section"><h2>{escape(title)}</h2>{body}</section>'


def _html_kv_table(mapping: dict[str, object], keys: list[str]) -> str:
    rows = []
    for key in keys:
        rows.append((key, _format_text(mapping.get(key))))
    return _html_table(["Field", "Value"], rows)


def _html_optional_preview_section(title: str, records: list[dict[str, object]], keys: list[str]) -> str:
    if not records:
        return ""
    body = _html_preview_block(records, keys)
    return f'<div class="subsection"><h3>{escape(title)}</h3>{body}</div>'


def _html_optional_window_extrema_section(window_summary: dict[str, object]) -> str:
    rows = [
        _flatten_window_metric_entry("best_prediction_ic_window", window_summary.get("best_prediction_ic_window")),
        _flatten_window_metric_entry("worst_prediction_ic_window", window_summary.get("worst_prediction_ic_window")),
        _flatten_window_metric_entry("best_prediction_rank_ic_window", window_summary.get("best_prediction_rank_ic_window")),
        _flatten_window_metric_entry("worst_prediction_rank_ic_window", window_summary.get("worst_prediction_rank_ic_window")),
    ]
    if not any(row.get("window_id") for row in rows):
        return ""
    return '<div class="subsection"><h3>Best and Worst Windows</h3>' + _html_table(
        ["window_type", "window_id", "prediction_ic", "prediction_rank_ic", "mse", "mae"],
        [tuple(_format_text(row.get(key)) for key in ["window_type", "window_id", "prediction_ic", "prediction_rank_ic", "mse", "mae"]) for row in rows],
    ) + "</div>"


def _html_visual_summary_section(
    *,
    window_summary: dict[str, object],
    portfolio_summary: dict[str, object],
    visual_summary: dict[str, object],
) -> str:
    positive_rank_ic_windows = window_summary.get("positive_prediction_rank_ic_windows")
    window_count = window_summary.get("window_count")
    mean_rank_ic = window_summary.get("mean_prediction_rank_ic")
    cumulative_return = portfolio_summary.get("cumulative_return")
    sharpe = portfolio_summary.get("sharpe")

    if positive_rank_ic_windows is not None and window_count is not None:
        positive_rank_ic_text = f"{_format_text(positive_rank_ic_windows)}/{_format_text(window_count)}"
    else:
        positive_rank_ic_text = "n/a"

    kpi_cards = "".join(
        [
            _html_visual_metric_card("Positive Rank IC Windows", positive_rank_ic_text),
            _html_visual_metric_card("Mean Rank IC", mean_rank_ic),
            _html_visual_metric_card("Cumulative Return", cumulative_return),
            _html_visual_metric_card("Sharpe", sharpe),
        ]
    )

    rank_ic_windows = visual_summary.get("rank_ic_windows", [])
    if not isinstance(rank_ic_windows, list):
        rank_ic_windows = []
    rank_ic_svg = _html_rank_ic_bar_svg(rank_ic_windows)
    rank_ic_panel = _html_visual_chart_panel(
        "Window-Level Prediction Rank IC",
        rank_ic_svg,
        (
            "Each bar is one out-of-sample walk-forward test window, so the chart makes ranking stability easy to compare "
            "across time. Positive bars indicate positive Rank IC, negative bars indicate inverse ranking, and the best "
            "and worst windows are emphasized with stronger outlines and label markers."
        ),
        (
            '<div class="chart-legend">'
            '<span><span class="legend-swatch legend-positive"></span>Positive Rank IC</span>'
            '<span><span class="legend-swatch legend-negative"></span>Negative Rank IC</span>'
            '<span><span class="legend-swatch legend-best"></span>Best window</span>'
            '<span><span class="legend-swatch legend-worst"></span>Worst window</span>'
            "</div>"
        ),
        (
            "No window-level prediction Rank IC values were available, so the out-of-sample ranking chart is omitted."
        ),
    )

    portfolio_points = visual_summary.get("portfolio_cumulative_return_points", [])
    if not isinstance(portfolio_points, list):
        portfolio_points = []
    portfolio_svg = _html_cumulative_return_svg(
        portfolio_points,
        final_cumulative_return=visual_summary.get("portfolio_final_cumulative_return"),
    )
    portfolio_panel = _html_visual_chart_panel(
        "Prediction Portfolio Cumulative Return",
        portfolio_svg,
        (
            "Gross-of-cost cumulative return computed from long_short_ret. Transaction costs are not modeled in this "
            "E2E report."
        ),
        "",
        "Prediction portfolio returns parquet is unavailable, so the cumulative return chart is omitted.",
    )

    body = (
        '<p class="note">Visual diagnostics summarizing the out-of-sample ranking signal and the gross-of-cost '
        "prediction portfolio are embedded directly in this report as inline SVG.</p>"
        f'<div class="visual-summary-grid">{kpi_cards}</div>'
        f'<div class="visual-charts">{rank_ic_panel}{portfolio_panel}</div>'
    )
    return _html_section("Visual Summary", body)


def _html_visual_metric_card(label: str, value: object) -> str:
    return (
        '<div class="visual-card">'
        f'<div class="visual-card-label">{escape(label)}</div>'
        f'<div class="visual-card-value">{escape(_format_text(value))}</div>'
        "</div>"
    )


def _html_visual_chart_panel(
    title: str,
    svg_markup: str,
    caption: str,
    legend_html: str = "",
    missing_caption: str = "",
) -> str:
    parts = [f"<h3>{escape(title)}</h3>"]
    if legend_html:
        parts.append(legend_html)
    if svg_markup:
        parts.append(f'<div class="svg-scroll">{svg_markup}</div>')
        parts.append(f'<p class="chart-caption">{escape(caption)}</p>')
    else:
        parts.append(f'<p class="chart-caption">{escape(missing_caption or caption)}</p>')
    return '<div class="visual-chart">' + "".join(parts) + "</div>"


def _html_rank_ic_bar_svg(windows: list[dict[str, object]]) -> str:
    values = [_safe_float(window.get("prediction_rank_ic")) for window in windows]
    finite_values = [value for value in values if value is not None]
    if not windows or not finite_values:
        return ""

    width = max(860, len(windows) * 48 + 120)
    height = 332
    left = 58
    right = 20
    top = 36
    bottom = 74
    plot_width = width - left - right
    plot_height = height - top - bottom

    min_value = min(finite_values + [0.0])
    max_value = max(finite_values + [0.0])
    if min_value == max_value:
        pad = 0.1 if max_value == 0 else abs(max_value) * 0.15
        min_value -= pad
        max_value += pad

    def _y(value: float) -> float:
        return top + ((max_value - value) / (max_value - min_value)) * plot_height

    zero_y = _y(0.0)
    slot_width = plot_width / len(windows)
    bar_width = max(12.0, min(30.0, slot_width * 0.62))

    pieces = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-labelledby="rank-ic-chart-title rank-ic-chart-desc">',
        '<title id="rank-ic-chart-title">Window-Level Prediction Rank IC</title>',
        (
            '<desc id="rank-ic-chart-desc">Bar chart of out-of-sample prediction Rank IC values for each '
            "walk-forward test window. Positive bars show stable ranking, negative bars show reversed ranking."
            "</desc>"
        ),
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        f'<line x1="{left}" y1="{zero_y:.2f}" x2="{width - right}" y2="{zero_y:.2f}" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="6 4"/>',
        f'<line x1="{left}" y1="{top}" x2="{width - right}" y2="{top}" stroke="#eef3fb" stroke-width="1"/>',
        f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="#eef3fb" stroke-width="1"/>',
    ]

    guide_values: list[float] = []
    for candidate in (max_value, 0.0, min_value):
        if all(abs(candidate - existing) > 1e-12 for existing in guide_values):
            guide_values.append(candidate)

    for label_value in guide_values:
        line_y = _y(label_value)
        pieces.append(
            f'<text x="{left - 10}" y="{line_y + 4:.2f}" text-anchor="end" fill="#5d6878" font-size="11">'
            f"{escape(_format_text(label_value))}</text>"
        )

    for index, window in enumerate(windows):
        window_id = window.get("window_id")
        original_value = values[index]
        value = original_value if original_value is not None else 0.0
        label = _short_window_label(window_id, index=index)
        if window.get("is_best"):
            label = f"{label}*"
        if window.get("is_worst"):
            label = f"{label}!"

        if value is None:
            value = 0.0
        bar_top = _y(value) if value >= 0 else zero_y
        bar_height = max(1.0, abs(_y(value) - zero_y))
        bar_left = left + (index * slot_width) + ((slot_width - bar_width) / 2.0)
        fill = "#1f8a54" if value > 0 else "#c63d4f" if value < 0 else "#94a3b8"
        stroke = "#2457a6" if window.get("is_best") else "#0f172a" if window.get("is_worst") else "#d7dfea"
        stroke_width = "2.5" if window.get("is_best") or window.get("is_worst") else "1"
        stroke_dasharray = ' stroke-dasharray="5 3"' if window.get("is_worst") else ""
        title_value = _format_text(original_value)
        title_text = f"{_format_text(window_id)}: rank IC {title_value}"
        if window.get("is_best"):
            title_text += " (best window)"
        if window.get("is_worst"):
            title_text += " (worst window)"
        pieces.append(
            '<g>'
            f'<title>{escape(title_text)}</title>'
            f'<rect x="{bar_left:.2f}" y="{bar_top:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{stroke_dasharray} rx="4" ry="4"/>'
            f'<text x="{bar_left + bar_width / 2.0:.2f}" y="{height - 28}" text-anchor="middle" fill="#5d6878" font-size="11">'
            f"{escape(label)}</text>"
            "</g>"
        )

    pieces.append("</svg>")
    return "".join(pieces)


def _html_cumulative_return_svg(
    portfolio_points: list[dict[str, object]],
    *,
    final_cumulative_return: object | None,
) -> str:
    values = [_safe_float(point.get("cumulative_return")) for point in portfolio_points]
    finite_values = [value for value in values if value is not None]
    if not portfolio_points or not finite_values:
        return ""

    width = 980
    height = 320
    left = 60
    right = 24
    top = 28
    bottom = 58
    plot_width = width - left - right
    plot_height = height - top - bottom

    min_value = min(finite_values + [0.0])
    max_value = max(finite_values + [0.0])
    if min_value == max_value:
        pad = 0.1 if max_value == 0 else abs(max_value) * 0.15
        min_value -= pad
        max_value += pad

    def _y(value: float) -> float:
        return top + ((max_value - value) / (max_value - min_value)) * plot_height

    zero_y = _y(0.0)
    if len(portfolio_points) == 1:
        x_positions = [left + (plot_width / 2.0)]
    else:
        x_positions = [left + (index / (len(portfolio_points) - 1)) * plot_width for index in range(len(portfolio_points))]

    y_positions = [_y(value if value is not None else 0.0) for value in values]
    line_segments = [f"M {x_positions[0]:.2f} {y_positions[0]:.2f}"]
    for x_pos, y_pos in zip(x_positions[1:], y_positions[1:]):
        line_segments.append(f"L {x_pos:.2f} {y_pos:.2f}")
    line_path = " ".join(line_segments)
    area_path = (
        f"{line_path} L {x_positions[-1]:.2f} {zero_y:.2f} L {x_positions[0]:.2f} {zero_y:.2f} Z"
    )

    final_value = _safe_float(final_cumulative_return)
    if final_value is None:
        final_value = finite_values[-1]
    final_text = _format_text(final_value)
    annotation_width = 212
    annotation_x = width - right - annotation_width

    pieces = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-labelledby="portfolio-chart-title portfolio-chart-desc">',
        '<title id="portfolio-chart-title">Prediction Portfolio Cumulative Return</title>',
        (
            '<desc id="portfolio-chart-desc">Line chart of cumulative gross long-short return derived from the prediction '
            "portfolio over time. The chart shows the zero line and the final cumulative return annotation."
            "</desc>"
        ),
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        f'<line x1="{left}" y1="{zero_y:.2f}" x2="{width - right}" y2="{zero_y:.2f}" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="6 4"/>',
        f'<path d="{area_path}" fill="#2457a6" fill-opacity="0.08" stroke="none"/>',
        f'<path d="{line_path}" fill="none" stroke="#2457a6" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>',
        f'<circle cx="{x_positions[-1]:.2f}" cy="{y_positions[-1]:.2f}" r="4.8" fill="#2457a6" stroke="#ffffff" stroke-width="2"/>',
        f'<rect x="{annotation_x}" y="12" width="{annotation_width}" height="30" rx="15" fill="#eef3fb" stroke="#d7dfea"/>',
        f'<text x="{annotation_x + annotation_width / 2.0:.2f}" y="31" text-anchor="middle" fill="#1c2430" font-size="11" font-weight="600">'
        f"Final cumulative return {escape(final_text)}</text>",
    ]

    guide_values = []
    for candidate in (max_value, 0.0, min_value):
        if all(abs(candidate - existing) > 1e-12 for existing in guide_values):
            guide_values.append(candidate)

    for label_value in guide_values:
        line_y = _y(label_value)
        pieces.append(
            f'<text x="{left - 10}" y="{line_y + 4:.2f}" text-anchor="end" fill="#5d6878" font-size="11">'
            f"{escape(_format_text(label_value))}</text>"
        )

    tick_indices = sorted({0, len(portfolio_points) - 1, len(portfolio_points) // 4, len(portfolio_points) // 2, (len(portfolio_points) * 3) // 4})
    for index in tick_indices:
        x_pos = x_positions[index]
        date_label = _format_text(portfolio_points[index].get("date"))
        if len(date_label) >= 7:
            date_label = date_label[:7]
        pieces.append(
            f'<line x1="{x_pos:.2f}" y1="{height - bottom}" x2="{x_pos:.2f}" y2="{height - bottom + 7}" stroke="#d7dfea" stroke-width="1"/>'
        )
        pieces.append(
            f'<text x="{x_pos:.2f}" y="{height - 10}" text-anchor="middle" fill="#5d6878" font-size="11">'
            f"{escape(date_label)}</text>"
        )

    pieces.append("</svg>")
    return "".join(pieces)


def _safe_float(value: object) -> float | None:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, np.generic):
        value = value.item()
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric):
        return None
    return json_safe_float(numeric)


def _short_window_label(window_id: object, index: int | None = None) -> str:
    text = _format_text(window_id)
    if text == "n/a":
        return f"W{index + 1}" if index is not None else text
    if "_test_" in text:
        candidate = text.rsplit("_test_", 1)[-1]
    elif "test_" in text:
        candidate = text.rsplit("test_", 1)[-1]
    else:
        candidate = text
    candidate = candidate.strip("_- ")
    if not candidate:
        return f"W{index + 1}" if index is not None else text
    if len(candidate) > 12 and index is not None:
        return f"W{index + 1}"
    return candidate


def _html_preview_block(records: list[dict[str, object]], keys: list[str]) -> str:
    rows = [tuple(_format_text(record.get(key)) for key in keys) for record in records]
    return _html_table([_title_case(key) for key in keys], rows)


def _html_bullet_list(items: list[object]) -> str:
    if not items:
        return "<p class=\"note\">n/a</p>"
    return "<ul>" + "".join(f"<li>{escape(_format_text(item))}</li>" for item in items) + "</ul>"


def _html_table(headers: list[str], rows: list[tuple[str, ...]]) -> str:
    if not rows:
        rows = [tuple("n/a" for _ in headers)]
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{_html_cell_value(cell)}</td>" for cell in row)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _html_cell_value(value: object) -> str:
    text = _format_text(value)
    if text == "n/a":
        return "n/a"
    return escape(text)


def _format_text(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return f"{value:.4f}" if pd.notna(value) else "n/a"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return ", ".join(_format_text(item) for item in value)
    return str(value)


def _title_case(value: str) -> str:
    return value.replace("_", " ").title()


def _normalize_json_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, np.generic):
        return _normalize_json_value(value.item())
    if isinstance(value, dict):
        return {str(key): _normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, float):
        return float(value) if pd.notna(value) else None
    if isinstance(value, int):
        return int(value)
    return value
