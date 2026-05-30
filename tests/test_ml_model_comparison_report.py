from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from scripts.build_ml_model_comparison_report import build_comparison, load_run_record, parse_run_specs


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ml_model_comparison"
RIDGE_RUN = FIXTURES / "ridge_run"
RF_RUN = FIXTURES / "rf_run"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build_ml_model_comparison_report.py"


def test_parse_run_specs_requires_model_name_path_pairs() -> None:
    assert parse_run_specs([f"ridge={RIDGE_RUN}"]) == [("ridge", RIDGE_RUN)]
    with pytest.raises(ValueError, match="expected model_name=/path/to/run_dir"):
        parse_run_specs([str(RIDGE_RUN)])


def test_load_run_record_extracts_prediction_and_holdout_metrics() -> None:
    record = load_run_record("ridge_regressor", RIDGE_RUN)

    assert record["model_name"] == "ridge_regressor"
    assert record["overall_mae"] == 0.080
    assert record["prediction_rank_ic_mean"] == 0.40
    assert record["has_research_validation"] is True
    assert record["validation_mode"] == "single_symbol_projection"
    assert record["validation_symbol"] == "A"
    assert record["holdout_total_return"] == 0.120
    assert record["holdout_sharpe_ratio"] == 1.10


def test_load_run_record_allows_missing_research_validation() -> None:
    record = load_run_record("random_forest_regressor", RF_RUN)

    assert record["has_research_validation"] is False
    assert record["holdout_total_return"] is None
    assert record["overall_mae"] == 0.120


def test_build_comparison_ranks_lower_error_first() -> None:
    records = [
        load_run_record("ridge_regressor", RIDGE_RUN),
        load_run_record("random_forest_regressor", RF_RUN),
    ]

    comparison = build_comparison(records, sort_by="overall_mae")

    assert comparison["model_name"].tolist() == ["ridge_regressor", "random_forest_regressor"]
    assert comparison["comparison_rank"].tolist() == [1, 2]


def test_script_writes_comparison_csv_and_summary(tmp_path: Path) -> None:
    output_dir = tmp_path / "comparison"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run",
            f"ridge_regressor={RIDGE_RUN}",
            "--run",
            f"random_forest_regressor={RF_RUN}",
            "--output-dir",
            str(output_dir),
            "--sort-by",
            "overall_mae",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode == 0, result.stderr
    comparison_path = output_dir / "model_comparison.csv"
    summary_path = output_dir / "model_comparison_summary.json"
    assert comparison_path.exists()
    assert summary_path.exists()

    comparison = pd.read_csv(comparison_path)
    assert comparison["model_name"].tolist() == ["ridge_regressor", "random_forest_regressor"]
    assert "holdout_sharpe_ratio" in comparison.columns

    with open(summary_path) as f:
        summary = json.load(f)
    assert summary["status"] == "ok"
    assert summary["stage"] == "ml_model_comparison_report"
    assert summary["model_count"] == 2
    assert summary["best_model"] == "ridge_regressor"
    assert summary["has_any_research_validation"] is True
    assert "does not train models" in summary["boundary"]
