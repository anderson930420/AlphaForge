from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


PIPELINE_ARTIFACTS: tuple[str, ...] = (
    "return_labels.csv",
    "supervised_panel.csv",
    "dataset.csv",
    "predictions.csv",
    "metrics_summary.json",
    "ml_signal.csv",
    "smoke_summary.json",
    "report.html",
)

TABLE_ARTIFACTS = {
    "return_labels": "return_labels.csv",
    "supervised_panel": "supervised_panel.csv",
    "dataset": "dataset.csv",
    "predictions": "predictions.csv",
    "ml_signal": "ml_signal.csv",
}

JSON_ARTIFACTS = {
    "metrics_summary": "metrics_summary.json",
    "smoke_summary": "smoke_summary.json",
}


@dataclass(frozen=True)
class TableSummary:
    name: str
    path: str
    exists: bool
    row_count: int | None = None
    column_count: int | None = None
    columns: tuple[str, ...] = ()
    preview_rows: tuple[dict[str, Any], ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class DashboardArtifactBundle:
    artifact_dir: str
    expected_files: tuple[str, ...]
    present_files: tuple[str, ...]
    missing_files: tuple[str, ...]
    table_summaries: dict[str, TableSummary]
    json_summaries: dict[str, dict[str, Any]]
    report_path: str | None
    report_exists: bool

    @property
    def is_complete(self) -> bool:
        return not self.missing_files


def load_dashboard_artifacts(
    artifact_dir: Path | str,
    *,
    preview_rows: int = 5,
) -> DashboardArtifactBundle:
    """Load a local-first dashboard view over AlphaForge ML artifact files.

    This function intentionally avoids importing any UI framework. It is the
    testable data layer used by the optional Streamlit dashboard.
    """
    root = Path(artifact_dir).expanduser()
    present_files = []
    missing_files = []
    for filename in PIPELINE_ARTIFACTS:
        path = root / filename
        if path.exists():
            present_files.append(filename)
        else:
            missing_files.append(filename)

    table_summaries = {
        name: summarize_csv_artifact(root / filename, name=name, preview_rows=preview_rows)
        for name, filename in TABLE_ARTIFACTS.items()
    }
    json_summaries = {
        name: load_json_artifact(root / filename)
        for name, filename in JSON_ARTIFACTS.items()
        if (root / filename).exists()
    }
    report = root / "report.html"

    return DashboardArtifactBundle(
        artifact_dir=str(root),
        expected_files=PIPELINE_ARTIFACTS,
        present_files=tuple(present_files),
        missing_files=tuple(missing_files),
        table_summaries=table_summaries,
        json_summaries=json_summaries,
        report_path=str(report) if report.exists() else None,
        report_exists=report.exists(),
    )


def summarize_csv_artifact(
    path: Path | str,
    *,
    name: str,
    preview_rows: int = 5,
) -> TableSummary:
    path = Path(path)
    if not path.exists():
        return TableSummary(name=name, path=str(path), exists=False)

    try:
        frame = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - defensive for corrupted user artifacts
        return TableSummary(name=name, path=str(path), exists=True, error=str(exc))

    preview = frame.head(preview_rows).where(pd.notna(frame.head(preview_rows)), None)
    return TableSummary(
        name=name,
        path=str(path),
        exists=True,
        row_count=int(len(frame)),
        column_count=int(len(frame.columns)),
        columns=tuple(str(c) for c in frame.columns),
        preview_rows=tuple(preview.to_dict(orient="records")),
    )


def load_json_artifact(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"value": data}
    return data


def pipeline_step_statuses(bundle: DashboardArtifactBundle) -> list[dict[str, Any]]:
    """Return ordered dashboard rows for the end-to-end ML artifact pipeline."""
    labels = {
        "return_labels.csv": "Forward return labels",
        "supervised_panel.csv": "Feature-label join",
        "dataset.csv": "Supervised ML dataset",
        "predictions.csv": "Baseline ML predictions",
        "metrics_summary.json": "Prediction metrics",
        "ml_signal.csv": "custom_signal v0.2 signal",
        "report.html": "HTML artifact report",
        "smoke_summary.json": "Smoke summary",
    }
    present = set(bundle.present_files)
    return [
        {
            "artifact": filename,
            "stage": labels[filename],
            "status": "present" if filename in present else "missing",
        }
        for filename in PIPELINE_ARTIFACTS
    ]
