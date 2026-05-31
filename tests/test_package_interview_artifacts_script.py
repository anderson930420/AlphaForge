from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "package_interview_artifacts.sh"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f)


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def _write_packageable_run(run_dir: Path, *, nonzero: int = 2, extra_signal_dates: list[str] | None = None) -> None:
    _write_json(run_dir / "ml_demo_summary.json", {"status": "ok"})
    _write_csv(run_dir / "signal" / "ml_signal.csv", pd.DataFrame({"symbol": ["C"], "target_weight": [1.0]}))
    _write_json(run_dir / "research_validation" / "ml_demo_research_validation_summary.json", {
        "nonzero_target_weight_count": nonzero,
        "date_alignment": {"extra_signal_dates": extra_signal_dates or []},
    })
    final_holdout = run_dir / "research_validation" / "ml_signal_single_symbol_validation" / "final_holdout"
    _write_json(final_holdout / "metrics_summary.json", {"total_return": 0.01})
    _write_csv(final_holdout / "equity_curve.csv", pd.DataFrame({"datetime": ["2024-04-30"], "equity": [100000.0]}))
    _write_csv(final_holdout / "trade_log.csv", pd.DataFrame({"entry_datetime": ["2024-04-30"], "trade_net_return": [0.01]}))
    (run_dir / "interview_artifact_report.html").write_text("<html><body>demo</body></html>")


def test_package_interview_artifacts_script_writes_uploadable_zip(tmp_path: Path) -> None:
    run_dir = tmp_path / "interview_run"
    output_zip = tmp_path / "bundles" / "interview_run.zip"
    _write_packageable_run(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT), str(run_dir), str(output_zip)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode == 0, result.stderr
    assert output_zip.exists()
    assert "nonzero_target_weight_count=2" in result.stdout
    with zipfile.ZipFile(output_zip) as archive:
        names = set(archive.namelist())
    assert "interview_run/ml_demo_summary.json" in names
    assert "interview_run/research_validation/ml_demo_research_validation_summary.json" in names
    assert "interview_run/interview_artifact_report.html" in names


def test_package_interview_artifacts_script_rejects_all_flat_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "all_flat_run"
    output_zip = tmp_path / "all_flat_run.zip"
    _write_packageable_run(run_dir, nonzero=0)

    result = subprocess.run(
        ["bash", str(SCRIPT), str(run_dir), str(output_zip)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode != 0
    assert "nonzero_target_weight_count must be > 0" in result.stderr
    assert not output_zip.exists()


def test_package_interview_artifacts_script_rejects_missing_html_by_default(tmp_path: Path) -> None:
    run_dir = tmp_path / "missing_html_run"
    output_zip = tmp_path / "missing_html_run.zip"
    _write_packageable_run(run_dir)
    (run_dir / "interview_artifact_report.html").unlink()

    result = subprocess.run(
        ["bash", str(SCRIPT), str(run_dir), str(output_zip)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode != 0
    assert "interview_artifact_report.html missing" in result.stderr
    assert not output_zip.exists()


def test_package_interview_artifacts_script_can_allow_missing_html(tmp_path: Path) -> None:
    run_dir = tmp_path / "missing_html_allowed_run"
    output_zip = tmp_path / "missing_html_allowed_run.zip"
    _write_packageable_run(run_dir)
    (run_dir / "interview_artifact_report.html").unlink()

    result = subprocess.run(
        ["bash", str(SCRIPT), str(run_dir), str(output_zip), "--allow-missing-html"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode == 0, result.stderr
    assert output_zip.exists()
