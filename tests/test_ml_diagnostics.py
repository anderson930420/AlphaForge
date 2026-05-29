from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.ml_diagnostics import (
    build_prediction_error_by_date,
    build_prediction_ic_by_date,
    build_prediction_quantile_returns,
    load_predictions,
    run_ml_prediction_diagnostics,
    write_ml_prediction_diagnostics,
)


def _predictions() -> pd.DataFrame:
    return pd.DataFrame({
        "asset_id": ["A", "B", "C", "D", "A", "B", "C", "D"],
        "date": [
            "2024-01-15", "2024-01-20", "2024-01-25", "2024-01-30",
            "2024-02-15", "2024-02-20", "2024-02-25", "2024-02-28",
        ],
        "predicted_return": [0.01, 0.02, 0.03, 0.04, 0.011, 0.021, 0.031, 0.041],
        "ret_fwd_1m": [0.015, 0.025, 0.035, 0.045, 0.010, 0.020, 0.030, 0.040],
    })


class TestMLPredictionDiagnostics:
    def test_summary_contains_core_metrics(self):
        result = run_ml_prediction_diagnostics(_predictions(), quantiles=2)

        assert result.summary["prediction_col"] == "predicted_return"
        assert result.summary["label_col"] == "ret_fwd_1m"
        assert result.summary["row_count"] == 8
        assert result.summary["valid_row_count"] == 8
        assert result.summary["date_count"] == 2
        assert result.summary["asset_count"] == 4
        assert result.summary["prediction_ic_observation_count"] == 2
        assert result.summary["prediction_rank_ic_observation_count"] == 2
        assert result.summary["long_short_observation_count"] == 2
        assert result.summary["overall_mse"] is not None
        assert result.summary["overall_mae"] is not None

    def test_prediction_ic_and_rank_ic_are_computed_by_date(self):
        result = run_ml_prediction_diagnostics(_predictions(), quantiles=2)

        assert len(result.ic_by_date) == 2
        assert set(result.ic_by_date.columns) == {"date", "row_count", "prediction_ic", "prediction_rank_ic"}
        assert result.ic_by_date["prediction_ic"].notna().all()
        assert result.ic_by_date["prediction_rank_ic"].notna().all()

    def test_quantile_returns_and_long_short_spread(self):
        result = run_ml_prediction_diagnostics(_predictions(), quantiles=2)

        assert len(result.quantile_returns) == 4
        assert set(result.quantile_returns["quantile"]) == {"Q1", "Q2"}
        assert len(result.long_short_spread) == 2
        assert (result.long_short_spread["long_short_spread"] > 0).all()

    def test_error_by_date_contains_mse_mae_and_mean_error(self):
        result = run_ml_prediction_diagnostics(_predictions(), quantiles=2)

        assert len(result.error_by_date) == 2
        required = {"date", "row_count", "mse", "mae", "mean_error", "mean_prediction", "mean_label"}
        assert required.issubset(result.error_by_date.columns)
        assert result.error_by_date["mse"].notna().all()
        assert result.error_by_date["mae"].notna().all()

    def test_constant_predictions_skip_ic_and_quantile_returns(self):
        predictions = _predictions()
        predictions["predicted_return"] = 0.01

        result = run_ml_prediction_diagnostics(predictions, quantiles=2)

        assert result.ic_by_date["prediction_ic"].isna().all()
        assert result.ic_by_date["prediction_rank_ic"].isna().all()
        assert result.quantile_returns.empty
        assert result.long_short_spread.empty

    def test_missing_required_columns_raises(self):
        with pytest.raises(ValueError, match="Missing required columns"):
            run_ml_prediction_diagnostics(pd.DataFrame({"asset_id": ["A"]}))

    def test_quantiles_must_be_at_least_two(self):
        with pytest.raises(ValueError, match="quantiles"):
            run_ml_prediction_diagnostics(_predictions(), quantiles=1)

    def test_custom_column_names_work(self):
        predictions = pd.DataFrame({
            "permno": ["A", "B", "C", "D"],
            "yyyymm": ["2024-01-31"] * 4,
            "score": [1, 2, 3, 4],
            "label": [0.01, 0.02, 0.03, 0.04],
        })

        result = run_ml_prediction_diagnostics(
            predictions,
            prediction_col="score",
            label_col="label",
            asset_id_col="permno",
            date_col="yyyymm",
            quantiles=2,
        )

        assert result.summary["prediction_col"] == "score"
        assert result.summary["asset_id_col"] == "permno"
        assert result.summary["date_col"] == "yyyymm"
        assert result.summary["row_count"] == 4


class TestMLPredictionDiagnosticsHelpers:
    def test_build_prediction_ic_by_date_handles_too_few_rows(self):
        frame = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-31"]),
            "prediction": [1.0],
            "label": [0.01],
        })

        result = build_prediction_ic_by_date(frame, prediction_col="prediction", label_col="label", date_col="date")

        assert result.iloc[0]["row_count"] == 1
        assert pd.isna(result.iloc[0]["prediction_ic"])
        assert pd.isna(result.iloc[0]["prediction_rank_ic"])

    def test_build_prediction_quantile_returns_skips_thin_dates(self):
        frame = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-31", "2024-01-31"]),
            "prediction": [1.0, 2.0],
            "label": [0.01, 0.02],
        })

        result = build_prediction_quantile_returns(
            frame,
            prediction_col="prediction",
            label_col="label",
            date_col="date",
            quantiles=5,
        )

        assert result.empty

    def test_build_prediction_error_by_date_handles_empty_valid_rows(self):
        frame = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-31"]),
            "prediction": [None],
            "label": [None],
        })

        result = build_prediction_error_by_date(frame, prediction_col="prediction", label_col="label", date_col="date")

        assert result.iloc[0]["row_count"] == 0
        assert pd.isna(result.iloc[0]["mse"])
        assert pd.isna(result.iloc[0]["mae"])

    def test_load_predictions_supports_csv(self, tmp_path: Path):
        path = tmp_path / "predictions.csv"
        _predictions().to_csv(path, index=False)

        loaded = load_predictions(path)

        assert len(loaded) == 8
        assert "predicted_return" in loaded.columns

    def test_load_predictions_rejects_unknown_suffix(self):
        with pytest.raises(ValueError, match="Unsupported predictions suffix"):
            load_predictions(Path("predictions.xlsx"))

    def test_write_ml_prediction_diagnostics_outputs_all_artifacts(self, tmp_path: Path):
        result = run_ml_prediction_diagnostics(_predictions(), quantiles=2)

        paths = write_ml_prediction_diagnostics(result, tmp_path)

        expected = {
            "ml_prediction_summary",
            "ml_prediction_ic_timeseries",
            "ml_prediction_quantile_returns",
            "ml_prediction_long_short_spread",
            "ml_prediction_error_by_date",
        }
        assert set(paths) == expected
        for path in paths.values():
            assert Path(path).exists()
        with open(paths["ml_prediction_summary"]) as f:
            summary = json.load(f)
        assert summary["prediction_col"] == "predicted_return"


class TestMLPredictionDiagnosticsScript:
    def test_run_ml_prediction_diagnostics_script_writes_outputs(self, tmp_path: Path):
        predictions = tmp_path / "predictions.csv"
        output_dir = tmp_path / "ml_prediction_diagnostics"
        _predictions().to_csv(predictions, index=False)

        result = subprocess.run(
            [
                sys.executable,
                "scripts/run_ml_prediction_diagnostics.py",
                "--predictions", str(predictions),
                "--output-dir", str(output_dir),
                "--quantiles", "2",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": "src"},
        )

        assert result.returncode == 0, f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
        payload = json.loads(result.stdout)
        assert payload["status"] == "ok"
        assert (output_dir / "ml_prediction_summary.json").exists()
        assert (output_dir / "ml_prediction_ic_timeseries.csv").exists()
        assert (output_dir / "ml_prediction_quantile_returns.csv").exists()
