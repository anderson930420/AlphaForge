from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from alphaforge.ml_signal import ML_SIGNAL_SIGNAL_COLUMNS


FIXTURES = Path(__file__).resolve().parent / "fixtures"
FEATURES_CSV = FIXTURES / "return_labels" / "features.csv"
RETURNS_CSV = FIXTURES / "return_labels" / "monthly_returns.csv"
SMOKE_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_ml_artifact_smoke.py"


def _run_smoke(output_dir: Path, **extra_args: str) -> Path:
    argv = [
        sys.executable,
        str(SMOKE_SCRIPT),
        "--features", str(FEATURES_CSV),
        "--returns", str(RETURNS_CSV),
        "--output-dir", str(output_dir),
    ]
    for key, value in extra_args.items():
        argv.append(f"--{key.replace('_', '-')}")
        argv.append(str(value))

    result = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    if result.returncode != 0:
        raise RuntimeError(f"Smoke script failed: {result.stderr}\n{result.stdout}")
    return output_dir


class TestRunMlArtifactSmoke:
    def test_smoke_runs_successfully(self, tmp_path):
        output_dir = tmp_path / "smoke_out"
        _run_smoke(output_dir)
        summary_path = output_dir / "smoke_summary.json"
        assert summary_path.exists()
        with open(summary_path) as f:
            summary = json.load(f)
        assert summary["status"] == "ok"

    def test_all_expected_files_created(self, tmp_path):
        output_dir = tmp_path / "smoke_out"
        _run_smoke(output_dir)
        expected = [
            "return_labels.csv",
            "supervised_panel.csv",
            "dataset.csv",
            "predictions.csv",
            "metrics_summary.json",
            "ml_signal.csv",
            "report.html",
            "smoke_summary.json",
        ]
        for name in expected:
            assert (output_dir / name).exists(), f"Missing: {name}"

    def test_smoke_summary_has_ok_status(self, tmp_path):
        output_dir = tmp_path / "smoke_out"
        _run_smoke(output_dir)
        with open(output_dir / "smoke_summary.json") as f:
            summary = json.load(f)
        assert summary["status"] == "ok"

    def test_row_counts_are_positive(self, tmp_path):
        output_dir = tmp_path / "smoke_out"
        _run_smoke(output_dir)
        with open(output_dir / "smoke_summary.json") as f:
            summary = json.load(f)
        for key in [
            "return_labels_rows",
            "supervised_panel_rows",
            "dataset_rows",
            "predictions_rows",
            "ml_signal_rows",
        ]:
            assert summary[key] > 0, f"{key} should be positive, got {summary[key]}"

    def test_ml_signal_has_v02_columns(self, tmp_path):
        output_dir = tmp_path / "smoke_out"
        _run_smoke(output_dir)
        signal = pd.read_csv(output_dir / "ml_signal.csv")
        assert list(signal.columns) == list(ML_SIGNAL_SIGNAL_COLUMNS)

    def test_ml_signal_directions_are_valid(self, tmp_path):
        output_dir = tmp_path / "smoke_out"
        _run_smoke(output_dir)
        signal = pd.read_csv(output_dir / "ml_signal.csv")
        for d in signal["direction"].unique():
            assert int(d) in {-1, 0, 1}

    def test_metrics_summary_has_expected_keys(self, tmp_path):
        output_dir = tmp_path / "smoke_out"
        _run_smoke(output_dir)
        with open(output_dir / "metrics_summary.json") as f:
            metrics = json.load(f)
        for key in ["row_count", "mse", "mae", "mean_prediction", "mean_label"]:
            assert key in metrics, f"Missing key: {key}"

    def test_report_html_exists_and_nonempty(self, tmp_path):
        output_dir = tmp_path / "smoke_out"
        _run_smoke(output_dir)
        report = output_dir / "report.html"
        assert report.exists()
        assert report.stat().st_size > 0

    def test_smoke_is_deterministic(self, tmp_path):
        output_dir1 = tmp_path / "run1"
        output_dir2 = tmp_path / "run2"
        _run_smoke(output_dir1)
        _run_smoke(output_dir2)

        signal1 = pd.read_csv(output_dir1 / "ml_signal.csv")
        signal2 = pd.read_csv(output_dir2 / "ml_signal.csv")
        pd.testing.assert_frame_equal(signal1, signal2)

        with open(output_dir1 / "smoke_summary.json") as f:
            summary1 = json.load(f)
        with open(output_dir2 / "smoke_summary.json") as f:
            summary2 = json.load(f)
        for key in [
            "status",
            "return_labels_rows",
            "supervised_panel_rows",
            "dataset_rows",
            "predictions_rows",
            "ml_signal_rows",
        ]:
            assert summary1[key] == summary2[key], f"Mismatch on {key}"

    def test_output_dir_not_under_artifacts(self, tmp_path):
        output_dir = tmp_path / "smoke_out"
        _run_smoke(output_dir)
        assert "artifacts" not in str(tmp_path)
