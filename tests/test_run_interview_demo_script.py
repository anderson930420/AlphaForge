from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from alphaforge.ml_models import _require_sklearn


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_interview_demo.sh"


def _require_sklearn_test() -> bool:
    try:
        _require_sklearn()
        return True
    except ImportError:
        return False


SKLEARN_AVAILABLE = _require_sklearn_test()


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_run_interview_demo_script_self_checks_and_renders_report(tmp_path: Path) -> None:
    output_dir = tmp_path / "interview_demo"

    result = subprocess.run(
        ["bash", str(SCRIPT), str(output_dir)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode == 0, result.stderr
    assert "Health checks passed" in result.stdout

    summary_path = output_dir / "research_validation" / "ml_demo_research_validation_summary.json"
    report_path = output_dir / "interview_artifact_report.html"
    assert summary_path.exists()
    assert report_path.exists()

    with open(summary_path) as f:
        summary = json.load(f)
    assert summary["symbol"] == "C"
    assert summary["nonzero_target_weight_count"] > 0
    assert summary["date_alignment"]["extra_signal_dates"] == []
    assert summary["all_flat_selected_symbol"] is False
