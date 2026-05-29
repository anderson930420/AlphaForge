from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.ml_models import _require_sklearn
from alphaforge.ml_signal import ML_SIGNAL_SIGNAL_COLUMNS


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ml_demo_pipeline"
FEATURES_CSV = FIXTURES / "features.csv"
RETURNS_CSV = FIXTURES / "monthly_returns.csv"
PIPELINE_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_ml_demo_pipeline.py"


def _require_sklearn_test() -> bool:
    try:
        _require_sklearn()
        return True
    except ImportError:
        return False


SKLEARN_AVAILABLE = _require_sklearn_test()


def _run_pipeline(output_dir: Path, **extra_args: str) -> Path:
    argv = [
        sys.executable,
        str(PIPELINE_SCRIPT),
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
        raise RuntimeError(f"Pipeline script failed (rc={result.returncode}): {result.stderr}\n{result.stdout}")
    return output_dir


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
class TestRunMlDemoPipeline:
    def test_script_exits_zero(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        assert (output_dir / "ml_demo_summary.json").exists()

    def test_return_labels_csv_exists(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        assert (output_dir / "return_labels.csv").exists()

    def test_supervised_panel_csv_exists(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        assert (output_dir / "supervised_panel.csv").exists()

    def test_model_predictions_csv_exists(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        assert (output_dir / "model" / "predictions.csv").exists()

    def test_model_metrics_json_exists(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        assert (output_dir / "model" / "metrics.json").exists()

    def test_model_feature_importance_csv_exists(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        assert (output_dir / "model" / "feature_importance.csv").exists()

    def test_ml_prediction_summary_json_exists(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        assert (output_dir / "ml_prediction_diagnostics" / "ml_prediction_summary.json").exists()

    def test_signal_ml_signal_csv_exists(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        assert (output_dir / "signal" / "ml_signal.csv").exists()

    def test_ml_demo_summary_status_ok(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        with open(output_dir / "ml_demo_summary.json") as f:
            summary = json.load(f)
        assert summary["status"] == "ok"

    def test_predictions_csv_has_required_columns(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        preds = pd.read_csv(output_dir / "model" / "predictions.csv")
        required = {"asset_id", "date", "predicted_return", "ret_fwd_1m"}
        assert required.issubset(set(preds.columns))

    def test_signal_has_v02_required_columns(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        signal = pd.read_csv(output_dir / "signal" / "ml_signal.csv")
        assert list(signal.columns) == list(ML_SIGNAL_SIGNAL_COLUMNS)

    def test_ml_demo_summary_contains_boundary_note(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        with open(output_dir / "ml_demo_summary.json") as f:
            summary = json.load(f)
        assert "boundary_note" in summary
        assert "research/demo" in summary["boundary_note"].lower()

    def test_non_empty_outputs(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        return_labels = pd.read_csv(output_dir / "return_labels.csv")
        assert len(return_labels) > 0

        supervised = pd.read_csv(output_dir / "supervised_panel.csv")
        assert len(supervised) > 0

        preds = pd.read_csv(output_dir / "model" / "predictions.csv")
        assert len(preds) > 0

        signal = pd.read_csv(output_dir / "signal" / "ml_signal.csv")
        assert len(signal) > 0

        with open(output_dir / "ml_prediction_diagnostics" / "ml_prediction_summary.json") as f:
            diag = json.load(f)
        assert diag["row_count"] > 0

    def test_no_external_data_dependency(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        with open(output_dir / "ml_demo_summary.json") as f:
            summary = json.load(f)
        assert summary["status"] == "ok"

    def test_return_labels_has_expected_columns(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        labels = pd.read_csv(output_dir / "return_labels.csv")
        required = {"asset_id", "date", "target_date", "horizon_months", "ret_fwd_1m", "source"}
        assert required.issubset(set(labels.columns))

    def test_supervised_panel_has_expected_columns(self, tmp_path: Path):
        output_dir = tmp_path / "pipeline_out"
        _run_pipeline(
            output_dir,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        panel = pd.read_csv(output_dir / "supervised_panel.csv")
        for col in ["asset_id", "date", "Mom12m", "BM", "Investment", "ret_fwd_1m"]:
            assert col in panel.columns, f"Missing column: {col}"

    def test_pipeline_is_deterministic(self, tmp_path: Path):
        output_dir1 = tmp_path / "run1"
        output_dir2 = tmp_path / "run2"
        _run_pipeline(
            output_dir1,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )
        _run_pipeline(
            output_dir2,
            model="ridge_regressor",
            feature_cols="Mom12m,BM,Investment",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            long_quantile="0.8",
            short_quantile="0.2",
            diagnostic_quantiles="2",
        )

        preds1 = pd.read_csv(output_dir1 / "model" / "predictions.csv")
        preds2 = pd.read_csv(output_dir2 / "model" / "predictions.csv")
        pd.testing.assert_frame_equal(preds1, preds2)

        signal1 = pd.read_csv(output_dir1 / "signal" / "ml_signal.csv")
        signal2 = pd.read_csv(output_dir2 / "signal" / "ml_signal.csv")
        pd.testing.assert_frame_equal(signal1, signal2)

        with open(output_dir1 / "ml_demo_summary.json") as f:
            s1 = json.load(f)
        with open(output_dir2 / "ml_demo_summary.json") as f:
            s2 = json.load(f)
        for key in ["status", "return_labels_rows", "supervised_panel_rows", "predictions_rows", "ml_signal_rows"]:
            assert s1[key] == s2[key], f"Mismatch on {key}"
