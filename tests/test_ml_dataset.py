from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from alphaforge.ml_dataset import build_ml_dataset, infer_ml_feature_cols, time_train_test_split


FIXTURES = Path(__file__).parent / "fixtures" / "ml_baseline"


def _load_fixture() -> pd.DataFrame:
    return pd.read_csv(FIXTURES / "supervised_panel.csv")


class TestInferMlFeatureCols:
    def test_infer_ml_feature_cols_excludes_leakage_prefixes(self):
        df = pd.DataFrame({
            "asset_id": ["A", "B"],
            "date": ["2024-01-31", "2024-01-31"],
            "Mom12m": [0.1, 0.2],
            "BM": [0.5, 0.6],
            "ret_fwd_1m": [0.01, 0.02],
            "ret_fwd_3m": [0.03, 0.04],
            "predicted_return": [0.01, 0.02],
            "prediction_score": [0.3, 0.4],
            "output_score": [0.5, 0.6],
        })

        features = infer_ml_feature_cols(df)

        assert set(features) == {"Mom12m", "BM"}
        assert "ret_fwd_3m" not in features
        assert "predicted_return" not in features
        assert "prediction_score" not in features
        assert "output_score" not in features

    def test_infer_ml_feature_cols_excludes_custom_asset_date_label_columns(self):
        df = pd.DataFrame({
            "permno": ["A"],
            "month": ["2024-01-31"],
            "label": [0.01],
            "Mom12m": [0.1],
            "prediction_score": [0.2],
        })

        features = infer_ml_feature_cols(
            df,
            asset_id_col="permno",
            date_col="month",
            label_col="label",
        )

        assert features == ["Mom12m"]


class TestBuildMlDataset:
    def test_feature_inference_excludes_metadata_and_label(self):
        df = _load_fixture()
        result = build_ml_dataset(df)
        assert "asset_id" in result.columns
        assert "date" in result.columns
        assert "ret_fwd_1m" in result.columns
        assert "Mom12m" in result.columns
        assert "BM" in result.columns
        assert "Investment" in result.columns
        assert "target_date" not in result.columns
        assert "horizon_months" not in result.columns
        assert "source" not in result.columns

    def test_feature_inference_excludes_prediction_output_leakage_columns(self):
        df = pd.DataFrame({
            "asset_id": ["A", "B"],
            "date": ["2024-01-31", "2024-01-31"],
            "Mom12m": [0.1, 0.2],
            "ret_fwd_1m": [0.01, 0.02],
            "predicted_return": [0.01, 0.02],
            "prediction_score": [0.3, 0.4],
            "output_score": [0.5, 0.6],
        })

        result = build_ml_dataset(df)

        assert list(result.columns) == ["asset_id", "date", "Mom12m", "ret_fwd_1m"]

    def test_explicit_feature_cols(self):
        df = _load_fixture()
        result = build_ml_dataset(df, feature_cols=["Mom12m", "BM"])
        assert list(result.columns) == ["asset_id", "date", "Mom12m", "BM", "ret_fwd_1m"]

    def test_missing_label_rows_dropped(self):
        df = _load_fixture()
        result = build_ml_dataset(df, drop_missing_label=True)
        assert not result["ret_fwd_1m"].isna().any()

    def test_missing_feature_values_kept_by_default(self):
        df = _load_fixture()
        result = build_ml_dataset(df, drop_missing_features=False)
        assert result["BM"].isna().any()

    def test_missing_required_columns_raises(self):
        df = pd.DataFrame({"asset_id": ["A"], "date": ["2024-01-31"]})
        with pytest.raises(ValueError, match="Missing required columns"):
            build_ml_dataset(df, label_col="ret_fwd_1m")

    def test_date_normalization_to_month_end(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A"],
            "date": ["2024-01-15", "2024-02-20"],
            "Mom12m": [0.10, 0.11],
            "ret_fwd_1m": [0.02, -0.01],
        })
        result = build_ml_dataset(df, feature_cols=["Mom12m"])
        dates = result["date"].tolist()
        assert dates[0] == pd.Timestamp("2024-01-31")
        assert dates[1] == pd.Timestamp("2024-02-29")

    def test_ret_fwd_columns_excluded_from_feature_inference(self):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-31"],
            "Mom12m": [0.10],
            "BM": [0.50],
            "ret_fwd_1m": [0.02],
            "ret_fwd_3m": [0.05],
        })
        result = build_ml_dataset(df)
        assert "ret_fwd_1m" in result.columns
        assert "ret_fwd_3m" not in result.columns
        assert "Mom12m" in result.columns
        assert "BM" in result.columns


class TestTimeTrainTestSplit:
    def test_split_using_train_end(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A", "A"],
            "date": pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31", "2024-04-30"]),
            "Mom12m": [0.1, 0.11, 0.09, 0.12],
            "ret_fwd_1m": [0.02, -0.01, 0.03, 0.015],
        })
        train, test = time_train_test_split(df, train_end="2024-02-29")
        assert len(train) == 2
        assert len(test) == 2
        assert test["date"].min() == pd.Timestamp("2024-03-31")

    def test_split_using_train_end_and_test_start(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A", "A"],
            "date": pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31", "2024-04-30"]),
            "Mom12m": [0.1, 0.11, 0.09, 0.12],
            "ret_fwd_1m": [0.02, -0.01, 0.03, 0.015],
        })
        train, test = time_train_test_split(df, train_end="2024-01-31", test_start="2024-03-31")
        assert len(train) == 1
        assert len(test) == 2
        assert train["date"].max() <= pd.Timestamp("2024-01-31")
        assert test["date"].min() >= pd.Timestamp("2024-03-31")

    def test_empty_train_raises(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A"],
            "date": pd.to_datetime(["2024-03-31", "2024-04-30"]),
            "Mom12m": [0.09, 0.12],
            "ret_fwd_1m": [0.03, 0.015],
        })
        with pytest.raises(ValueError, match="Train set is empty"):
            time_train_test_split(df, train_end="2024-01-31")

    def test_empty_test_raises(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A"],
            "date": pd.to_datetime(["2024-01-31", "2024-02-29"]),
            "Mom12m": [0.1, 0.11],
            "ret_fwd_1m": [0.02, -0.01],
        })
        with pytest.raises(ValueError, match="Test set is empty"):
            time_train_test_split(df, train_end="2024-03-31")

    def test_no_train_end_or_test_start_raises(self):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": pd.to_datetime(["2024-01-31"]),
            "Mom12m": [0.1],
            "ret_fwd_1m": [0.02],
        })
        with pytest.raises(ValueError, match="At least one of train_end or test_start must be provided"):
            time_train_test_split(df)

    def test_string_date_column_split(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A", "A"],
            "date": ["2024-01-15", "2024-02-20", "2024-03-10", "2024-04-05"],
            "Mom12m": [0.1, 0.11, 0.09, 0.12],
            "ret_fwd_1m": [0.02, -0.01, 0.03, 0.015],
        })
        train, test = time_train_test_split(df, train_end="2024-02-28")
        assert len(train) == 2
        assert len(test) == 2
        assert test["date"].min() == pd.Timestamp("2024-03-31")
