from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from alphaforge.dashboard_artifacts import (
    PIPELINE_ARTIFACTS,
    load_dashboard_artifacts,
    pipeline_step_statuses,
    summarize_csv_artifact,
)


EXPECTED_TABLES = (
    "return_labels",
    "supervised_panel",
    "dataset",
    "predictions",
    "ml_signal",
)


def _write_minimal_artifacts(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "asset_id": ["A", "B"],
        "date": ["2024-01-31", "2024-01-31"],
        "target_date": ["2024-02-29", "2024-02-29"],
        "horizon_months": [1, 1],
        "ret_fwd_1m": [0.02, -0.01],
        "source": ["fixture", "fixture"],
    }).to_csv(root / "return_labels.csv", index=False)
    pd.DataFrame({
        "asset_id": ["A", "B"],
        "date": ["2024-01-31", "2024-01-31"],
        "Mom12m": [0.10, -0.05],
        "ret_fwd_1m": [0.02, -0.01],
    }).to_csv(root / "supervised_panel.csv", index=False)
    pd.DataFrame({
        "asset_id": ["A", "B"],
        "date": ["2024-01-31", "2024-01-31"],
        "Mom12m": [0.10, -0.05],
        "ret_fwd_1m": [0.02, -0.01],
    }).to_csv(root / "dataset.csv", index=False)
    pd.DataFrame({
        "asset_id": ["A", "B"],
        "date": ["2024-01-31", "2024-01-31"],
        "predicted_return": [0.015, -0.005],
        "ret_fwd_1m": [0.02, -0.01],
    }).to_csv(root / "predictions.csv", index=False)
    pd.DataFrame({
        "datetime": ["2024-01-31", "2024-01-31"],
        "available_at": ["2024-01-31", "2024-01-31"],
        "symbol": ["A", "B"],
        "asset_id": ["A", "B"],
        "signal_name": ["ml_predicted_return", "ml_predicted_return"],
        "score": [0.015, -0.005],
        "direction": [1, -1],
        "target_weight": [1.0, -1.0],
        "source": ["AlphaForgeML", "AlphaForgeML"],
    }).to_csv(root / "ml_signal.csv", index=False)
    (root / "metrics_summary.json").write_text(json.dumps({"row_count": 2, "mse": 0.1}))
    (root / "smoke_summary.json").write_text(json.dumps({"status": "ok", "dataset_rows": 2}))
    (root / "report.html").write_text("<html><body>AlphaForge report</body></html>")


class TestDashboardArtifacts:
    def test_load_dashboard_artifacts_reports_complete_bundle(self, tmp_path: Path):
        _write_minimal_artifacts(tmp_path)

        bundle = load_dashboard_artifacts(tmp_path)

        assert bundle.is_complete
        assert bundle.expected_files == PIPELINE_ARTIFACTS
        assert set(bundle.present_files) == set(PIPELINE_ARTIFACTS)
        assert bundle.missing_files == ()
        assert bundle.report_exists
        assert bundle.report_path is not None

    def test_load_dashboard_artifacts_reports_missing_files(self, tmp_path: Path):
        pd.DataFrame({"asset_id": ["A"], "date": ["2024-01-31"], "ret_fwd_1m": [0.01]}).to_csv(
            tmp_path / "dataset.csv",
            index=False,
        )

        bundle = load_dashboard_artifacts(tmp_path)

        assert not bundle.is_complete
        assert "dataset.csv" in bundle.present_files
        assert "ml_signal.csv" in bundle.missing_files
        assert not bundle.report_exists

    def test_table_summaries_include_shape_columns_and_preview(self, tmp_path: Path):
        _write_minimal_artifacts(tmp_path)

        bundle = load_dashboard_artifacts(tmp_path, preview_rows=1)

        assert set(bundle.table_summaries) == set(EXPECTED_TABLES)
        dataset = bundle.table_summaries["dataset"]
        assert dataset.exists
        assert dataset.row_count == 2
        assert dataset.column_count == 4
        assert dataset.columns == ("asset_id", "date", "Mom12m", "ret_fwd_1m")
        assert len(dataset.preview_rows) == 1

    def test_json_summaries_are_loaded(self, tmp_path: Path):
        _write_minimal_artifacts(tmp_path)

        bundle = load_dashboard_artifacts(tmp_path)

        assert bundle.json_summaries["metrics_summary"]["row_count"] == 2
        assert bundle.json_summaries["smoke_summary"]["status"] == "ok"

    def test_pipeline_step_statuses_are_ordered(self, tmp_path: Path):
        _write_minimal_artifacts(tmp_path)

        bundle = load_dashboard_artifacts(tmp_path)
        steps = pipeline_step_statuses(bundle)

        assert [step["artifact"] for step in steps] == list(PIPELINE_ARTIFACTS)
        assert all(step["status"] == "present" for step in steps)
        assert steps[0]["stage"] == "Forward return labels"

    def test_summarize_missing_csv_artifact(self, tmp_path: Path):
        summary = summarize_csv_artifact(tmp_path / "missing.csv", name="missing")

        assert not summary.exists
        assert summary.row_count is None
        assert summary.columns == ()
