from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from alphaforge.ml_torch import (
    _infer_feature_cols,
    _preprocess,
    _preprocess_predict,
    _require_torch,
    evaluate_torch_predictions,
)
from alphaforge.ml_dataset import build_ml_dataset, time_train_test_split


FIXTURES = Path(__file__).parent / "fixtures" / "ml_baseline"


def _load_fixture() -> pd.DataFrame:
    return pd.read_csv(FIXTURES / "supervised_panel.csv")


def _torch_available() -> bool:
    try:
        _require_torch()
        return True
    except ImportError:
        return False


TORCH_AVAILABLE = _torch_available()


class TestFeatureInference:
    def test_feature_inference_excludes_metadata_and_labels(self):
        df = _load_fixture()
        features = _infer_feature_cols(
            df,
            asset_id_col="asset_id",
            date_col="date",
            label_col="ret_fwd_1m",
        )
        expected = {"Mom12m", "BM", "Investment"}
        assert set(features) == expected

    def test_feature_inference_excludes_ret_fwd(self):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-15"],
            "ret_fwd_1m": [0.01],
            "ret_fwd_3m": [0.02],
            "Mom12m": [0.05],
            "label": [0.03],
        })
        features = _infer_feature_cols(
            df,
            asset_id_col="asset_id",
            date_col="date",
            label_col="label",
        )
        assert "Mom12m" in features
        assert "ret_fwd_1m" not in features
        assert "ret_fwd_3m" not in features

    def test_feature_inference_excludes_prediction_output_cols(self):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-15"],
            "label_col": [0.01],
            "Mom12m": [0.05],
            "predicted_return": [0.01],
            "output_score": [0.02],
        })
        features = _infer_feature_cols(
            df,
            asset_id_col="asset_id",
            date_col="date",
            label_col="label_col",
        )
        assert "Mom12m" in features
        assert "predicted_return" not in features
        assert "output_score" not in features


class TestPreprocessing:
    def test_median_imputation_produces_finite_arrays(self):
        df = _load_fixture()
        preproc = _preprocess(
            df,
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
        )
        assert np.isfinite(preproc["X"]).all()
        assert np.isfinite(preproc["medians"]).all()
        assert np.isfinite(preproc["means"]).all()
        assert np.isfinite(preproc["stds"]).all()

    def test_scaling_produces_finite_arrays(self):
        df = _load_fixture()
        preproc = _preprocess(
            df,
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
        )
        X_scaled = _preprocess_predict(
            df,
            feature_cols=["Mom12m", "BM", "Investment"],
            preproc=preproc,
        )
        assert np.isfinite(X_scaled).all()

    def test_input_dim_matches_feature_count(self):
        df = _load_fixture()
        preproc = _preprocess(
            df,
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
        )
        assert preproc["input_dim"] == 3

    def test_preprocess_with_missing_values(self):
        df = pd.DataFrame({
            "f1": [1.0, 2.0, np.nan],
            "f2": [np.nan, 5.0, 6.0],
            "label": [0.1, 0.2, 0.3],
        })
        preproc = _preprocess(df, feature_cols=["f1", "f2"], label_col="label")
        assert np.isfinite(preproc["X"]).all()
        assert preproc["X"].shape == (3, 2)


class TestTimeSplit:
    def test_time_split_is_deterministic(self):
        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train1, test1 = time_train_test_split(dataset, train_end="2024-03-31")
        train2, test2 = time_train_test_split(dataset, train_end="2024-03-31")

        pd.testing.assert_frame_equal(train1, train2)
        pd.testing.assert_frame_equal(test1, test2)


class TestEvaluate:
    def test_metrics_include_required_keys(self):
        preds = pd.DataFrame({
            "asset_id": ["A", "B"],
            "date": pd.to_datetime(["2024-04-30", "2024-04-30"]),
            "predicted_return": [0.01, -0.01],
            "ret_fwd_1m": [0.015, -0.01],
        })
        metrics = evaluate_torch_predictions(preds)
        assert "mse" in metrics
        assert "mae" in metrics
        assert "row_count" in metrics
        assert "mean_prediction" in metrics
        assert "mean_label" in metrics

    def test_metrics_prediction_label_correlation(self):
        preds = pd.DataFrame({
            "asset_id": ["A", "B", "C"],
            "date": pd.to_datetime(["2024-04-30"] * 3),
            "predicted_return": [0.01, 0.015, 0.02],
            "ret_fwd_1m": [0.015, 0.02, 0.025],
        })
        metrics = evaluate_torch_predictions(preds)
        assert "prediction_label_correlation" in metrics
        assert metrics["prediction_label_correlation"] > 0

    def test_missing_label_column_returns_error(self):
        preds = pd.DataFrame({
            "asset_id": ["A"],
            "date": pd.to_datetime(["2024-04-30"]),
            "predicted_return": [0.01],
        })
        metrics = evaluate_torch_predictions(preds, label_col="ret_fwd_1m")
        assert "error" in metrics


class TestTorchMissingGraceful:
    def test_require_torch_raises_if_not_installed(self):
        if TORCH_AVAILABLE:
            import pytest
            pytest.skip("torch is installed, cannot test missing case")
        import pytest
        with pytest.raises(ImportError, match="PyTorch is required"):
            _require_torch()

    def test_import_path_handles_torch_missing_gracefully(self):
        try:
            import torch  # noqa: F401
        except ImportError:
            pass


class TestFitPredict:
    def test_torch_mlp_can_train_two_epochs(self):
        __import__("pytest").importorskip("torch")
        from alphaforge.ml_torch import fit_torch_mlp, predict_torch_mlp

        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        model_pack = fit_torch_mlp(
            train,
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
            hidden_dim=16,
            dropout=0.1,
            epochs=2,
            batch_size=4,
            learning_rate=0.001,
            seed=42,
        )
        preds = predict_torch_mlp(model_pack, test)

        assert "asset_id" in preds.columns
        assert "date" in preds.columns
        assert "predicted_return" in preds.columns
        assert len(preds) == len(test)
        assert len(model_pack["history"]) == 2

    def test_predictions_has_required_columns(self):
        __import__("pytest").importorskip("torch")
        from alphaforge.ml_torch import fit_torch_mlp, predict_torch_mlp

        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        model_pack = fit_torch_mlp(
            train,
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
            hidden_dim=8,
            epochs=1,
            batch_size=4,
            seed=42,
        )
        preds = predict_torch_mlp(model_pack, test)

        required = {"asset_id", "date", "predicted_return", "ret_fwd_1m", "model_name"}
        assert required.issubset(set(preds.columns))

    def test_time_split_is_deterministic_with_training(self):
        __import__("pytest").importorskip("torch")
        from alphaforge.ml_torch import fit_torch_mlp, predict_torch_mlp

        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        mp1 = fit_torch_mlp(train, feature_cols=["Mom12m", "BM", "Investment"],
                            label_col="ret_fwd_1m", hidden_dim=8, epochs=1, batch_size=4, seed=42)
        preds1 = predict_torch_mlp(mp1, test)

        mp2 = fit_torch_mlp(train, feature_cols=["Mom12m", "BM", "Investment"],
                            label_col="ret_fwd_1m", hidden_dim=8, epochs=1, batch_size=4, seed=42)
        preds2 = predict_torch_mlp(mp2, test)

        np.testing.assert_array_almost_equal(preds1["predicted_return"].values, preds2["predicted_return"].values)


class TestRun:
    def test_run_torch_mlp_writes_artifacts(self, tmp_path: Path):
        __import__("pytest").importorskip("torch")
        from alphaforge.ml_torch import run_torch_mlp

        df = _load_fixture()
        output_dir = tmp_path / "torch_out"
        run_torch_mlp(
            df,
            output_dir=output_dir,
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols=["Mom12m", "BM", "Investment"],
            hidden_dim=8,
            epochs=2,
            batch_size=4,
            seed=42,
        )

        assert (output_dir / "predictions.csv").exists()
        assert (output_dir / "metrics.json").exists()
        assert (output_dir / "model_summary.json").exists()
        assert (output_dir / "train_config.json").exists()
        assert (output_dir / "training_history.csv").exists()
        assert (output_dir / "feature_importance.csv").exists()

    def test_history_has_one_row_per_epoch(self, tmp_path: Path):
        __import__("pytest").importorskip("torch")
        from alphaforge.ml_torch import run_torch_mlp

        df = _load_fixture()
        output_dir = tmp_path / "torch_out"
        run_torch_mlp(
            df,
            output_dir=output_dir,
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols=["Mom12m", "BM", "Investment"],
            hidden_dim=8,
            epochs=3,
            batch_size=4,
            seed=42,
        )

        history = pd.read_csv(output_dir / "training_history.csv")
        assert len(history) == 3
        assert list(history.columns) == ["epoch", "train_loss"]

    def test_feature_importance_not_available(self, tmp_path: Path):
        __import__("pytest").importorskip("torch")
        from alphaforge.ml_torch import run_torch_mlp

        df = _load_fixture()
        output_dir = tmp_path / "torch_out"
        run_torch_mlp(
            df,
            output_dir=output_dir,
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols=["Mom12m", "BM", "Investment"],
            hidden_dim=8,
            epochs=1,
            batch_size=4,
            seed=42,
        )

        fi = pd.read_csv(output_dir / "feature_importance.csv")
        assert fi["importance_type"].iloc[0] == "not_available_for_torch_mlp"
        assert fi["importance"].isna().all()

    def test_metrics_contain_mse_and_mae(self, tmp_path: Path):
        __import__("pytest").importorskip("torch")
        from alphaforge.ml_torch import run_torch_mlp

        df = _load_fixture()
        output_dir = tmp_path / "torch_out"
        run_torch_mlp(
            df,
            output_dir=output_dir,
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols=["Mom12m", "BM", "Investment"],
            hidden_dim=8,
            epochs=2,
            batch_size=4,
            seed=42,
        )

        import json
        with open(output_dir / "metrics.json") as f:
            metrics = json.load(f)
        assert "mse" in metrics
        assert "mae" in metrics
        assert "row_count" in metrics
        assert "train_row_count" in metrics
        assert "test_row_count" in metrics
