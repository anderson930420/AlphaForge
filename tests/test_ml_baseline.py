from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd

from alphaforge.ml_baseline import (
    evaluate_regression_predictions,
    fit_baseline_regressor,
    predict_baseline_regressor,
)
from alphaforge.ml_dataset import build_ml_dataset, time_train_test_split


FIXTURES = Path(__file__).parent / "fixtures" / "ml_baseline"


def _load_fixture() -> pd.DataFrame:
    return pd.read_csv(FIXTURES / "supervised_panel.csv")


class TestFitPredict:
    def test_model_fits_and_predicts_deterministic(self):
        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        model = fit_baseline_regressor(train, feature_cols=["Mom12m", "BM", "Investment"], label_col="ret_fwd_1m")
        preds = predict_baseline_regressor(model, test, feature_cols=["Mom12m", "BM", "Investment"])

        model2 = fit_baseline_regressor(train, feature_cols=["Mom12m", "BM", "Investment"], label_col="ret_fwd_1m")
        preds2 = predict_baseline_regressor(model2, test, feature_cols=["Mom12m", "BM", "Investment"])

        pd.testing.assert_frame_equal(preds, preds2)

    def test_predictions_include_asset_id_date_prediction_col(self):
        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        model = fit_baseline_regressor(train, feature_cols=["Mom12m", "BM", "Investment"], label_col="ret_fwd_1m")
        preds = predict_baseline_regressor(model, test, feature_cols=["Mom12m", "BM", "Investment"])

        required = {"asset_id", "date", "predicted_return"}
        assert required.issubset(set(preds.columns))
        assert len(preds) == len(test)

    def test_missing_features_imputed_not_crashing(self):
        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"], drop_missing_features=False)
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        model = fit_baseline_regressor(train, feature_cols=["Mom12m", "BM", "Investment"], label_col="ret_fwd_1m")
        preds = predict_baseline_regressor(model, test, feature_cols=["Mom12m", "BM", "Investment"])

        assert len(preds) == len(test)
        assert not preds["predicted_return"].isna().any()

    def test_custom_label_col_in_predictions(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A"],
            "date": ["2024-01-31", "2024-02-29", "2024-03-31"],
            "Mom12m": [0.10, 0.11, 0.09],
            "y": [0.02, -0.01, 0.03],
        })
        dataset = build_ml_dataset(df, label_col="y", feature_cols=["Mom12m"])
        train, test = time_train_test_split(dataset, train_end="2024-02-29")
        model = fit_baseline_regressor(train, feature_cols=["Mom12m"], label_col="y")
        preds = predict_baseline_regressor(model, test, feature_cols=["Mom12m"], label_col="y")
        assert "y" in preds.columns
        assert "predicted_return" in preds.columns
        metrics = evaluate_regression_predictions(preds, label_col="y")
        assert "mse" in metrics
        assert "mae" in metrics

    def test_all_nan_feature_in_train_does_not_crash(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A", "B", "B"],
            "date": ["2024-01-31", "2024-02-29", "2024-03-31", "2024-01-31", "2024-02-29"],
            "Mom12m": [0.10, 0.11, 0.09, 0.05, 0.06],
            "nan_feat": [float("nan"), float("nan"), float("nan"), 0.30, 0.31],
            "ret_fwd_1m": [0.02, -0.01, 0.03, -0.005, -0.02],
        })
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "nan_feat"])
        train, test = time_train_test_split(dataset, train_end="2024-02-29")
        model = fit_baseline_regressor(train, feature_cols=["Mom12m", "nan_feat"], label_col="ret_fwd_1m")
        preds = predict_baseline_regressor(model, test, feature_cols=["Mom12m", "nan_feat"])
        assert len(preds) == len(test)
        assert not preds["predicted_return"].isna().any()

    def test_custom_asset_id_and_date_cols(self):
        df = pd.DataFrame({
            "permno": ["A", "A", "A", "A"],
            "yyyymm": pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31", "2024-04-30"]),
            "Mom12m": [0.10, 0.11, 0.09, 0.12],
            "ret_fwd_1m": [0.02, -0.01, 0.03, 0.015],
        })
        dataset = build_ml_dataset(df, asset_id_col="permno", date_col="yyyymm", feature_cols=["Mom12m"])
        train, test = time_train_test_split(dataset, date_col="yyyymm", train_end="2024-02-29")
        model = fit_baseline_regressor(train, feature_cols=["Mom12m"], label_col="ret_fwd_1m")
        preds = predict_baseline_regressor(
            model, test, feature_cols=["Mom12m"],
            asset_id_col="permno", date_col="yyyymm", label_col="ret_fwd_1m",
        )
        assert list(preds.columns) == ["asset_id", "date", "predicted_return", "ret_fwd_1m"]
        assert preds["asset_id"].iloc[0] == "A"
        assert preds["date"].iloc[0] == pd.Timestamp("2024-03-31")


class TestEvaluate:
    def test_metrics_include_mse_mae_correlation(self):
        preds = pd.DataFrame({
            "asset_id": ["A", "B"],
            "date": pd.to_datetime(["2024-04-30", "2024-04-30"]),
            "predicted_return": [0.01, -0.01],
            "ret_fwd_1m": [0.015, -0.01],
        })
        metrics = evaluate_regression_predictions(preds)
        assert "mse" in metrics
        assert "mae" in metrics
        assert "correlation" in metrics
        assert "row_count" in metrics
        assert "mean_prediction" in metrics
        assert "mean_label" in metrics

    def test_metrics_handle_constant_predictions(self):
        preds = pd.DataFrame({
            "asset_id": ["A", "B", "C"],
            "date": pd.to_datetime(["2024-04-30"] * 3),
            "predicted_return": [0.0, 0.0, 0.0],
            "ret_fwd_1m": [0.015, -0.01, 0.02],
        })
        metrics = evaluate_regression_predictions(preds)
        assert "mse" in metrics
        assert "mae" in metrics

    def test_metrics_handle_too_few_rows(self):
        preds = pd.DataFrame({
            "asset_id": ["A"],
            "date": pd.to_datetime(["2024-04-30"]),
            "predicted_return": [0.01],
            "ret_fwd_1m": [0.015],
        })
        metrics = evaluate_regression_predictions(preds)
        assert "mse" in metrics
        assert "mae" in metrics
        assert metrics["row_count"] == 1

    def test_metrics_handle_empty(self):
        preds = pd.DataFrame({
            "asset_id": [],
            "date": pd.Series([], dtype="datetime64[ns]"),
            "predicted_return": [],
            "ret_fwd_1m": [],
        })
        metrics = evaluate_regression_predictions(preds)
        assert metrics["row_count"] == 0


class TestCLI:
    def test_run_ml_baseline_writes_outputs(self, tmp_path: Path):
        panel = FIXTURES / "supervised_panel.csv"
        output_dir = tmp_path / "ml_baseline"
        result = subprocess.run(
            [
                "python3", "-m", "alphaforge.cli", "run-ml-baseline",
                "--panel", str(panel),
                "--output-dir", str(output_dir),
                "--label-col", "ret_fwd_1m",
                "--train-end", "2024-03-31",
                "--feature-cols", "Mom12m,BM,Investment",
            ],
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "PYTHONPATH": "src"},
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        assert (output_dir / "dataset.csv").exists()
        assert (output_dir / "predictions.csv").exists()
        assert (output_dir / "metrics_summary.json").exists()

        dataset = pd.read_csv(output_dir / "dataset.csv")
        assert "asset_id" in dataset.columns
        assert "date" in dataset.columns
        assert "ret_fwd_1m" in dataset.columns

        predictions = pd.read_csv(output_dir / "predictions.csv")
        assert "predicted_return" in predictions.columns

        with open(output_dir / "metrics_summary.json") as f:
            metrics = json.load(f)
        assert "mse" in metrics
        assert "row_count" in metrics

    def test_run_ml_baseline_creates_output_dir(self, tmp_path: Path):
        panel = FIXTURES / "supervised_panel.csv"
        output_dir = tmp_path / "nonexistent" / "ml_baseline"
        result = subprocess.run(
            [
                "python3", "-m", "alphaforge.cli", "run-ml-baseline",
                "--panel", str(panel),
                "--output-dir", str(output_dir),
                "--label-col", "ret_fwd_1m",
                "--train-end", "2024-03-31",
                "--feature-cols", "Mom12m,BM,Investment",
                "--test-start", "2024-04-01",
            ],
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "PYTHONPATH": "src"},
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_dir.exists()
        assert (output_dir / "dataset.csv").exists()

    def test_cli_custom_asset_id_and_date_cols(self, tmp_path: Path):
        panel = tmp_path / "panel.csv"
        panel.write_text("permno,yyyymm,Mom12m,BM,ret_fwd_1m\n"
                         "A,2024-01-31,0.10,0.50,0.02\n"
                         "A,2024-02-29,0.11,0.51,-0.01\n"
                         "A,2024-03-31,0.09,0.52,0.03\n"
                         "A,2024-04-30,0.12,0.53,0.015\n"
                         "B,2024-01-31,0.05,0.30,-0.005\n"
                         "B,2024-02-29,0.06,0.31,-0.02\n"
                         "B,2024-03-31,0.04,0.32,0.015\n"
                         "B,2024-04-30,0.07,0.33,-0.01\n")
        output_dir = tmp_path / "ml_baseline"
        result = subprocess.run(
            [
                "python3", "-m", "alphaforge.cli", "run-ml-baseline",
                "--panel", str(panel),
                "--output-dir", str(output_dir),
                "--asset-id-col", "permno",
                "--date-col", "yyyymm",
                "--label-col", "ret_fwd_1m",
                "--train-end", "2024-03-31",
                "--feature-cols", "Mom12m,BM",
            ],
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "PYTHONPATH": "src"},
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        predictions = pd.read_csv(output_dir / "predictions.csv")
        assert "asset_id" in predictions.columns
        assert "date" in predictions.columns
        assert "predicted_return" in predictions.columns
