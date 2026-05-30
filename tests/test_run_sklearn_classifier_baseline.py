from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.ml_models import _require_sklearn


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ml_demo_pipeline"
FEATURES_CSV = FIXTURES / "features.csv"
RETURNS_CSV = FIXTURES / "monthly_returns.csv"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_sklearn_classifier_baseline.py"


def _require_sklearn_test() -> bool:
    try:
        _require_sklearn()
        return True
    except ImportError:
        return False


SKLEARN_AVAILABLE = _require_sklearn_test()


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_run_sklearn_classifier_baseline_writes_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "classifier_out"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--features",
            str(FEATURES_CSV),
            "--returns",
            str(RETURNS_CSV),
            "--output-dir",
            str(output_dir),
            "--classifier",
            "logistic_regression_classifier",
            "--feature-cols",
            "Mom12m,BM,Investment",
            "--return-label-col",
            "ret_fwd_1m",
            "--classification-label-col",
            "ret_fwd_1m_positive",
            "--classification-threshold",
            "0.0",
            "--train-end",
            "2024-03-31",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / "return_labels.csv").exists()
    assert (output_dir / "classification_labels.csv").exists()
    assert (output_dir / "supervised_classifier_panel.csv").exists()
    assert (output_dir / "classifier" / "predictions.csv").exists()
    assert (output_dir / "classifier" / "metrics.json").exists()
    assert (output_dir / "classifier" / "feature_importance.csv").exists()
    assert (output_dir / "classifier_baseline_summary.json").exists()

    predictions = pd.read_csv(output_dir / "classifier" / "predictions.csv")
    assert predictions["predicted_probability"].between(0.0, 1.0).all()
    assert set(predictions["predicted_class"].unique()).issubset({0, 1})

    with open(output_dir / "classifier" / "metrics.json") as f:
        metrics = json.load(f)
    assert metrics["row_count"] > 0
    assert "accuracy" in metrics
    assert "roc_auc" in metrics

    with open(output_dir / "classifier_baseline_summary.json") as f:
        summary = json.load(f)
    assert summary["status"] == "ok"
    assert summary["stage"] == "sklearn_classifier_baseline"
    assert summary["classifier"] == "logistic_regression_classifier"
    assert summary["does_generate_trading_signal"] is False
    assert summary["does_run_research_validation"] is False
    assert summary["does_execute_live_trades"] is False


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_run_sklearn_classifier_baseline_rejects_unknown_classifier(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--features",
            str(FEATURES_CSV),
            "--returns",
            str(RETURNS_CSV),
            "--output-dir",
            str(tmp_path / "out"),
            "--classifier",
            "not_a_classifier",
            "--feature-cols",
            "Mom12m,BM,Investment",
            "--train-end",
            "2024-03-31",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode != 0
    assert "invalid choice" in result.stderr
