from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.ml_torch import _require_torch


FIXTURES = Path(__file__).resolve().parent / "fixtures"
PANEL_CSV = FIXTURES / "ml_baseline" / "supervised_panel.csv"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_torch_mlp_baseline.py"


def _require_torch_test() -> bool:
    try:
        _require_torch()
        return True
    except ImportError:
        return False


TORCH_AVAILABLE = _require_torch_test()


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


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
class TestRunTorchMlpBaselineScript:
    def test_script_runs_successfully(self, tmp_path: Path):
        output_dir = tmp_path / "torch_out"
        _run_script(
            output_dir,
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols="Mom12m,BM,Investment",
            epochs="2",
            batch_size="4",
            hidden_dim="8",
            learning_rate="0.001",
            weight_decay="0.0001",
            dropout="0.1",
            seed="42",
        )
        assert output_dir.exists()

    def test_output_files_exist(self, tmp_path: Path):
        output_dir = tmp_path / "torch_out"
        _run_script(
            output_dir,
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols="Mom12m,BM,Investment",
            epochs="2",
            batch_size="4",
            hidden_dim="8",
        )
        for name in [
            "train_config.json",
            "model_summary.json",
            "training_history.csv",
            "predictions.csv",
            "metrics.json",
            "feature_importance.csv",
        ]:
            assert (output_dir / name).exists(), f"Missing: {name}"

    def test_predictions_csv_has_required_columns(self, tmp_path: Path):
        output_dir = tmp_path / "torch_out"
        _run_script(
            output_dir,
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols="Mom12m,BM,Investment",
            epochs="2",
            batch_size="4",
            hidden_dim="8",
        )
        preds = pd.read_csv(output_dir / "predictions.csv")
        required = {"asset_id", "date", "predicted_return", "ret_fwd_1m", "model_name"}
        assert required.issubset(set(preds.columns))

    def test_training_history_has_one_row_per_epoch(self, tmp_path: Path):
        output_dir = tmp_path / "torch_out"
        _run_script(
            output_dir,
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols="Mom12m,BM,Investment",
            epochs="3",
            batch_size="4",
            hidden_dim="8",
        )
        history = pd.read_csv(output_dir / "training_history.csv")
        assert len(history) == 3
        assert list(history.columns) == ["epoch", "train_loss"]

    def test_metrics_json_contains_mse_and_mae(self, tmp_path: Path):
        output_dir = tmp_path / "torch_out"
        _run_script(
            output_dir,
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols="Mom12m,BM,Investment",
            epochs="2",
            batch_size="4",
            hidden_dim="8",
        )
        with open(output_dir / "metrics.json") as f:
            metrics = json.load(f)
        assert "mse" in metrics
        assert "mae" in metrics
        assert "row_count" in metrics
        assert "train_row_count" in metrics
        assert "test_row_count" in metrics

    def test_model_summary_json_contains_model_name(self, tmp_path: Path):
        output_dir = tmp_path / "torch_out"
        _run_script(
            output_dir,
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols="Mom12m,BM,Investment",
            epochs="2",
            batch_size="4",
            hidden_dim="8",
        )
        with open(output_dir / "model_summary.json") as f:
            summary = json.load(f)
        assert summary["model_name"] == "torch_mlp_regressor"
        assert summary["model_type"] == "torch_mlp_regressor"
        assert summary["torch_required"] is True
        assert "feature_cols" in summary
        assert "train_end" in summary
        assert "hidden_dim" in summary
        assert "dropout" in summary
        assert "epochs" in summary

    def test_script_infers_features_when_omitted(self, tmp_path: Path):
        output_dir = tmp_path / "torch_infer"
        _run_script(
            output_dir,
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            epochs="1",
            batch_size="4",
            hidden_dim="8",
        )
        preds = pd.read_csv(output_dir / "predictions.csv")
        required = {"asset_id", "date", "predicted_return", "ret_fwd_1m"}
        assert required.issubset(set(preds.columns))
        with open(output_dir / "metrics.json") as f:
            metrics = json.load(f)
        assert "mse" in metrics

    def test_script_with_missing_torch_reports_clear_error(self, tmp_path: Path, monkeypatch):
        if TORCH_AVAILABLE:
            pytest.skip("torch is installed, cannot test missing case with subprocess")
        argv = [
            sys.executable,
            str(SCRIPT),
            "--panel", str(PANEL_CSV),
            "--output-dir", str(tmp_path / "torch_out"),
            "--label-col", "ret_fwd_1m",
            "--train-end", "2024-03-31",
            "--epochs", "1",
            "--batch-size", "4",
            "--hidden-dim", "8",
        ]
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "PYTHONPATH": "src"},
        )
        assert result.returncode != 0
        assert "PyTorch is required" in result.stderr or "PyTorch is required" in result.stdout
