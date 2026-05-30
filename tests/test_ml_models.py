from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from alphaforge.ml_models import (
    _require_sklearn,
    evaluate_sklearn_predictions,
    fit_sklearn_model,
    predict_sklearn_model,
    run_sklearn_ml_model,
)
from alphaforge.ml_dataset import build_ml_dataset, infer_ml_feature_cols, time_train_test_split


FIXTURES = Path(__file__).parent / "fixtures" / "ml_baseline"


def _load_fixture() -> pd.DataFrame:
    return pd.read_csv(FIXTURES / "supervised_panel.csv")


def _require_sklearn_test() -> bool:
    try:
        _require_sklearn()
        return True
    except ImportError:
        return False


SKLEARN_AVAILABLE = _require_sklearn_test()


class TestFeatureInference:
    def test_sklearn_uses_shared_inference_excluding_prediction_output_columns(self):
        df = pd.DataFrame({
            "asset_id": ["A", "B", "A", "B"],
            "date": ["2024-01-31", "2024-01-31", "2024-02-29", "2024-02-29"],
            "Mom12m": [0.1, 0.2, 0.3, 0.4],
            "BM": [0.5, 0.6, 0.7, 0.8],
            "ret_fwd_1m": [0.01, 0.02, 0.03, 0.04],
            "ret_fwd_3m": [0.05, 0.06, 0.07, 0.08],
            "predicted_return": [0.2, 0.3, 0.4, 0.5],
            "prediction_score": [0.1, 0.2, 0.3, 0.4],
            "output_score": [0.9, 0.8, 0.7, 0.6],
        })

        features = infer_ml_feature_cols(df)

        assert set(features) == {"Mom12m", "BM"}
        assert "predicted_return" not in features
        assert "prediction_score" not in features
        assert "output_score" not in features
        assert "ret_fwd_3m" not in features

    def test_run_sklearn_ml_model_raises_when_no_features_are_inferred(self, tmp_path: Path):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        df = pd.DataFrame({
            "asset_id": ["A", "A"],
            "date": ["2024-01-31", "2024-02-29"],
            "ret_fwd_1m": [0.01, 0.02],
            "predicted_return": [0.03, 0.04],
            "prediction_score": [0.05, 0.06],
            "output_score": [0.07, 0.08],
        })

        import pytest
        with pytest.raises(ValueError, match="At least one ML feature column is required"):
            run_sklearn_ml_model(
                df,
                model_name="ridge_regressor",
                output_dir=tmp_path / "out",
                label_col="ret_fwd_1m",
                train_end="2024-01-31",
            )


class TestFitPredict:
    def test_ridge_regressor_fits_and_predicts(self):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        model_pack = fit_sklearn_model(
            train,
            model_name="ridge_regressor",
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
        )
        preds = predict_sklearn_model(model_pack, test)

        assert "asset_id" in preds.columns
        assert "date" in preds.columns
        assert "predicted_return" in preds.columns
        assert len(preds) == len(test)

    def test_random_forest_regressor_fits_and_predicts(self):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        model_pack = fit_sklearn_model(
            train,
            model_name="random_forest_regressor",
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
        )
        preds = predict_sklearn_model(model_pack, test)

        assert "asset_id" in preds.columns
        assert "date" in preds.columns
        assert "predicted_return" in preds.columns
        assert len(preds) == len(test)

    def test_hist_gradient_boosting_regressor_fits_and_predicts(self):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        model_pack = fit_sklearn_model(
            train,
            model_name="hist_gradient_boosting_regressor",
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
        )
        preds = predict_sklearn_model(model_pack, test)

        assert "asset_id" in preds.columns
        assert "date" in preds.columns
        assert "predicted_return" in preds.columns
        assert len(preds) == len(test)

    def test_missing_features_imputed(self):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"], drop_missing_features=False)
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        model_pack = fit_sklearn_model(
            train,
            model_name="ridge_regressor",
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
        )
        preds = predict_sklearn_model(model_pack, test)

        assert len(preds) == len(test)
        assert not preds["predicted_return"].isna().any()

    def test_time_split_is_deterministic(self):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train1, test1 = time_train_test_split(dataset, train_end="2024-03-31")
        train2, test2 = time_train_test_split(dataset, train_end="2024-03-31")

        model_pack1 = fit_sklearn_model(
            train1,
            model_name="ridge_regressor",
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
        )
        preds1 = predict_sklearn_model(model_pack1, test1)

        model_pack2 = fit_sklearn_model(
            train2,
            model_name="ridge_regressor",
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
        )
        preds2 = predict_sklearn_model(model_pack2, test2)

        assert list(preds1["asset_id"]) == list(preds2["asset_id"])
        assert list(preds1["date"]) == list(preds2["date"])
        np.testing.assert_array_almost_equal(preds1["predicted_return"].values, preds2["predicted_return"].values)

    def test_predictions_has_required_columns(self):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        model_pack = fit_sklearn_model(
            train,
            model_name="ridge_regressor",
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
        )
        preds = predict_sklearn_model(model_pack, test)

        required = {"asset_id", "date", "predicted_return", "ret_fwd_1m"}
        assert required.issubset(set(preds.columns))

    def test_feature_importance_has_expected_columns(self):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        from alphaforge.ml_models import _extract_feature_importance
        model_pack = fit_sklearn_model(
            train,
            model_name="random_forest_regressor",
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
        )
        fi = _extract_feature_importance(
            model_pack["model"],
            model_pack["feature_cols"],
            model_pack["model_name"],
        )
        expected = {"feature", "importance", "importance_type", "model_name"}
        assert set(fi.columns) == expected
        assert len(fi) == len(model_pack["feature_cols"])

    def test_unsupported_model_raises(self):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        with __import__("pytest").raises(ValueError, match="Unsupported model name"):
            fit_sklearn_model(
                train,
                model_name="unsupported_model",
                feature_cols=["Mom12m"],
                label_col="ret_fwd_1m",
            )

    def test_ridge_coefficient_importance(self):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        df = _load_fixture()
        dataset = build_ml_dataset(df, feature_cols=["Mom12m", "BM", "Investment"])
        train, test = time_train_test_split(dataset, train_end="2024-03-31")

        from alphaforge.ml_models import _extract_feature_importance
        model_pack = fit_sklearn_model(
            train,
            model_name="ridge_regressor",
            feature_cols=["Mom12m", "BM", "Investment"],
            label_col="ret_fwd_1m",
        )
        fi = _extract_feature_importance(
            model_pack["model"],
            model_pack["feature_cols"],
            model_pack["model_name"],
        )
        assert fi["importance_type"].iloc[0] == "coefficient"
        assert fi["importance"].notna().all()


class TestEvaluate:
    def test_metrics_include_required_keys(self):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        preds = pd.DataFrame({
            "asset_id": ["A", "B"],
            "date": pd.to_datetime(["2024-04-30", "2024-04-30"]),
            "predicted_return": [0.01, -0.01],
            "ret_fwd_1m": [0.015, -0.01],
        })
        metrics = evaluate_sklearn_predictions(preds)
        assert "mse" in metrics
        assert "mae" in metrics
        assert "row_count" in metrics
        assert "mean_prediction" in metrics
        assert "mean_label" in metrics

    def test_metrics_prediction_label_correlation(self):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        preds = pd.DataFrame({
            "asset_id": ["A", "B", "C"],
            "date": pd.to_datetime(["2024-04-30"] * 3),
            "predicted_return": [0.01, 0.015, 0.02],
            "ret_fwd_1m": [0.015, 0.02, 0.025],
        })
        metrics = evaluate_sklearn_predictions(preds)
        assert "prediction_label_correlation" in metrics
        assert metrics["prediction_label_correlation"] > 0


class TestRun:
    def test_run_sklearn_ml_model_writes_artifacts(self, tmp_path: Path):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        df = _load_fixture()
        output_dir = tmp_path / "sklearn_out"
        run_sklearn_ml_model(
            df,
            model_name="ridge_regressor",
            output_dir=output_dir,
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols=["Mom12m", "BM", "Investment"],
        )

        assert (output_dir / "predictions.csv").exists()
        assert (output_dir / "metrics.json").exists()
        assert (output_dir / "model_summary.json").exists()
        assert (output_dir / "train_config.json").exists()
        assert (output_dir / "feature_importance.csv").exists()

    def test_run_sklearn_ml_model_with_two_models(self, tmp_path: Path):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        df = _load_fixture()
        for model_name in ["ridge_regressor", "hist_gradient_boosting_regressor"]:
            output_dir = tmp_path / model_name
            run_sklearn_ml_model(
                df,
                model_name=model_name,
                output_dir=output_dir,
                label_col="ret_fwd_1m",
                train_end="2024-03-31",
                feature_cols=["Mom12m", "BM", "Investment"],
            )
            assert (output_dir / "predictions.csv").exists()
            with open(output_dir / "model_summary.json") as f:
                summary = json.load(f)
            assert summary["model_name"] == model_name

    def test_unsupported_model_in_run_raises(self, tmp_path: Path):
        if not SKLEARN_AVAILABLE:
            import pytest
            pytest.skip("scikit-learn not installed")
        df = _load_fixture()
        import pytest
        with pytest.raises(ValueError, match="Unsupported model name"):
            run_sklearn_ml_model(
                df,
                model_name="unsupported_model",
                output_dir=tmp_path / "out",
                label_col="ret_fwd_1m",
                train_end="2024-03-31",
                feature_cols=["Mom12m", "BM", "Investment"],
            )
