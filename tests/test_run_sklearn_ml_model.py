from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.ml_models import _require_sklearn


FIXTURES = Path(__file__).resolve().parent / "fixtures"
PANEL_CSV = FIXTURES / "ml_baseline" / "supervised_panel.csv"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_sklearn_ml_model.py"


def _require_sklearn_test() -> bool:
    try:
        _require_sklearn()
        return True
    except ImportError:
        return False


SKLEARN_AVAILABLE = _require_sklearn_test()


def _run_script(output_dir: Path, **extra_args: str) -> Path:
    argv = [
        sys.executable,
        str(SCRIPT),
        "--panel", str(PANEL_CSV),
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
        raise RuntimeError(f"Script failed: {result.stderr}\n{result.stdout}")
    return output_dir


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
class TestRunSklearnMlModelScript:
    def test_script_runs_successfully(self, tmp_path: Path):
        output_dir = tmp_path / "sklearn_out"
        _run_script(
            output_dir,
            model="ridge_regressor",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols="Mom12m,BM,Investment",
        )
        assert output_dir.exists()

    def test_output_files_exist(self, tmp_path: Path):
        output_dir = tmp_path / "sklearn_out"
        _run_script(
            output_dir,
            model="ridge_regressor",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols="Mom12m,BM,Investment",
        )
        for name in [
            "predictions.csv",
            "metrics.json",
            "model_summary.json",
            "train_config.json",
            "feature_importance.csv",
        ]:
            assert (output_dir / name).exists(), f"Missing: {name}"

    def test_predictions_csv_has_required_columns(self, tmp_path: Path):
        output_dir = tmp_path / "sklearn_out"
        _run_script(
            output_dir,
            model="ridge_regressor",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols="Mom12m,BM,Investment",
        )
        preds = pd.read_csv(output_dir / "predictions.csv")
        required = {"asset_id", "date", "predicted_return", "ret_fwd_1m"}
        assert required.issubset(set(preds.columns))

    def test_metrics_json_contains_mse_and_mae(self, tmp_path: Path):
        output_dir = tmp_path / "sklearn_out"
        _run_script(
            output_dir,
            model="ridge_regressor",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols="Mom12m,BM,Investment",
        )
        with open(output_dir / "metrics.json") as f:
            metrics = json.load(f)
        assert "mse" in metrics
        assert "mae" in metrics
        assert "row_count" in metrics
        assert "train_row_count" in metrics
        assert "test_row_count" in metrics

    def test_model_summary_json_contains_model_name(self, tmp_path: Path):
        output_dir = tmp_path / "sklearn_out"
        _run_script(
            output_dir,
            model="ridge_regressor",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols="Mom12m,BM,Investment",
        )
        with open(output_dir / "model_summary.json") as f:
            summary = json.load(f)
        assert summary["model_name"] == "ridge_regressor"
        assert summary["sklearn_required"] is True
        assert "feature_cols" in summary
        assert "train_end" in summary

    def test_feature_importance_csv_exists(self, tmp_path: Path):
        output_dir = tmp_path / "sklearn_out"
        _run_script(
            output_dir,
            model="ridge_regressor",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols="Mom12m,BM,Investment",
        )
        fi = pd.read_csv(output_dir / "feature_importance.csv")
        assert "feature" in fi.columns
        assert "importance" in fi.columns
        assert "importance_type" in fi.columns
        assert "model_name" in fi.columns

    def test_tree_model_works(self, tmp_path: Path):
        output_dir = tmp_path / "sklearn_tree"
        _run_script(
            output_dir,
            model="random_forest_regressor",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols="Mom12m,BM,Investment",
        )
        assert (output_dir / "predictions.csv").exists()
        fi = pd.read_csv(output_dir / "feature_importance.csv")
        assert fi["importance_type"].iloc[0] == "feature_importances_"

    def test_script_infers_features_when_omitted(self, tmp_path: Path):
        output_dir = tmp_path / "sklearn_infer"
        _run_script(
            output_dir,
            model="ridge_regressor",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
        )
        preds = pd.read_csv(output_dir / "predictions.csv")
        required = {"asset_id", "date", "predicted_return", "ret_fwd_1m"}
        assert required.issubset(set(preds.columns))
        with open(output_dir / "metrics.json") as f:
            metrics = json.load(f)
        assert "mse" in metrics
