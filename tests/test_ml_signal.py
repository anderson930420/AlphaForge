from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.ml_signal import (
    ML_SIGNAL_SIGNAL_COLUMNS,
    build_ml_prediction_signal,
    load_prediction_panel,
)


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ml_signal"
PREDICTIONS_CSV = FIXTURES / "predictions.csv"
PREDICTIONS_PARQUET = FIXTURES / "predictions.parquet"


class TestLoadPredictionPanel:
    def test_load_csv(self):
        df = load_prediction_panel(PREDICTIONS_CSV)
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["asset_id", "date", "predicted_return", "ret_fwd_1m"]
        assert len(df) == 10

    def test_load_parquet(self):
        df = load_prediction_panel(PREDICTIONS_PARQUET)
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["asset_id", "date", "predicted_return", "ret_fwd_1m"]
        assert len(df) == 10

    def test_unsupported_suffix_raises(self):
        with pytest.raises(ValueError, match="Unsupported prediction file suffix"):
            load_prediction_panel(Path("data.xlsx"))


class TestBuildMlPredictionSignal:
    def test_csv_prediction_works(self):
        df = pd.read_csv(PREDICTIONS_CSV)
        result = build_ml_prediction_signal(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_parquet_prediction_works(self):
        df = pd.read_parquet(PREDICTIONS_PARQUET)
        result = build_ml_prediction_signal(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_output_schema_is_v02(self):
        df = pd.read_csv(PREDICTIONS_CSV)
        result = build_ml_prediction_signal(df)
        assert list(result.columns) == list(ML_SIGNAL_SIGNAL_COLUMNS)

    def test_date_normalization_to_month_end(self):
        df = pd.DataFrame({
            "asset_id": ["X"],
            "date": ["2024-01-15"],
            "predicted_return": [0.05],
        })
        result = build_ml_prediction_signal(df)
        assert str(result.loc[0, "datetime"])[:10] == "2024-01-31"

    def test_symbol_defaults_to_asset_id(self):
        df = pd.read_csv(PREDICTIONS_CSV)
        result = build_ml_prediction_signal(df)
        assert all(result["symbol"] == result["asset_id"])

    def test_custom_symbol_col_works(self):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-31"],
            "predicted_return": [0.05],
            "ticker": ["AAPL"],
        })
        result = build_ml_prediction_signal(df, symbol_col="ticker")
        assert result.loc[0, "symbol"] == "AAPL"

    def test_available_at_defaults_to_datetime(self):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-15"],
            "predicted_return": [0.05],
        })
        result = build_ml_prediction_signal(df)
        assert result.loc[0, "available_at"] == result.loc[0, "datetime"]

    def test_custom_available_at_col_works(self):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-15"],
            "predicted_return": [0.05],
            "available_at": ["2024-01-20"],
        })
        result = build_ml_prediction_signal(df, available_at_col="available_at")
        assert str(result.loc[0, "available_at"])[:10] == "2024-01-31"
        assert str(result.loc[0, "datetime"])[:10] == "2024-01-31"

    def test_long_short_neutral_directions_by_date(self):
        df = pd.read_csv(PREDICTIONS_CSV)
        result = build_ml_prediction_signal(df, long_quantile=0.8, short_quantile=0.2)

        jan = result[result["datetime"] == pd.Timestamp("2024-01-31")]
        assert set(jan["direction"].unique()) <= {-1, 0, 1}
        long_jan = jan[jan["direction"] == 1]
        short_jan = jan[jan["direction"] == -1]
        neutral_jan = jan[jan["direction"] == 0]
        assert len(long_jan) > 0
        assert len(short_jan) > 0
        assert len(neutral_jan) > 0

        feb = result[result["datetime"] == pd.Timestamp("2024-02-29")]
        long_feb = feb[feb["direction"] == 1]
        short_feb = feb[feb["direction"] == -1]
        neutral_feb = feb[feb["direction"] == 0]
        assert len(long_feb) > 0
        assert len(short_feb) > 0
        assert len(neutral_feb) > 0

    def test_nan_predictions_become_neutral(self):
        df = pd.read_csv(PREDICTIONS_CSV)
        result = build_ml_prediction_signal(df)

        feb = result[result["datetime"] == pd.Timestamp("2024-02-29")]
        feb_c = feb[feb["asset_id"] == "C"]
        assert len(feb_c) == 1
        assert feb_c.iloc[0]["direction"] == 0
        assert feb_c.iloc[0]["target_weight"] == 0.0

    def test_target_weights_normalized_per_date(self):
        df = pd.read_csv(PREDICTIONS_CSV)
        result = build_ml_prediction_signal(df, gross_long_weight=1.0, gross_short_weight=-1.0)

        for date_val in result["datetime"].unique():
            date_rows = result[result["datetime"] == date_val]
            long_sum = date_rows[date_rows["direction"] == 1]["target_weight"].sum()
            short_sum = date_rows[date_rows["direction"] == -1]["target_weight"].sum()
            neutral_sum = date_rows[date_rows["direction"] == 0]["target_weight"].sum()

            if (date_rows["direction"] == 1).any():
                assert abs(long_sum - 1.0) < 0.001
            if (date_rows["direction"] == -1).any():
                assert abs(short_sum - (-1.0)) < 0.001
            assert neutral_sum == 0.0

    def test_missing_required_columns_raises(self):
        df = pd.DataFrame({"asset_id": ["A"], "date": ["2024-01-31"]})
        with pytest.raises(ValueError, match="Missing required columns"):
            build_ml_prediction_signal(df)

    def test_invalid_short_quantile_raises(self):
        df = pd.DataFrame({"asset_id": ["A"], "date": ["2024-01-31"], "predicted_return": [0.05]})
        with pytest.raises(ValueError, match="short_quantile"):
            build_ml_prediction_signal(df, short_quantile=-0.1)

        with pytest.raises(ValueError, match="short_quantile"):
            build_ml_prediction_signal(df, short_quantile=1.5)

    def test_invalid_long_quantile_raises(self):
        df = pd.DataFrame({"asset_id": ["A"], "date": ["2024-01-31"], "predicted_return": [0.05]})
        with pytest.raises(ValueError, match="long_quantile"):
            build_ml_prediction_signal(df, long_quantile=-0.1)

        with pytest.raises(ValueError, match="long_quantile"):
            build_ml_prediction_signal(df, long_quantile=1.5)

    def test_short_not_less_than_long_raises(self):
        df = pd.DataFrame({"asset_id": ["A"], "date": ["2024-01-31"], "predicted_return": [0.05]})
        with pytest.raises(ValueError, match="must be less than"):
            build_ml_prediction_signal(df, short_quantile=0.5, long_quantile=0.3)

    def test_realized_labels_are_ignored(self):
        df = pd.DataFrame({
            "asset_id": ["A", "B"],
            "date": ["2024-01-31", "2024-01-31"],
            "predicted_return": [0.10, -0.10],
            "ret_fwd_1m": [0.05, -0.15],
        })
        result = build_ml_prediction_signal(df, long_quantile=0.6, short_quantile=0.4)
        assert "ret_fwd_1m" not in result.columns

    def test_realized_labels_not_required(self):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-31"],
            "predicted_return": [0.05],
        })
        result = build_ml_prediction_signal(df)
        assert len(result) == 1

    def test_custom_column_names_work(self):
        df = pd.DataFrame({
            "permno": [10001],
            "yyyymm": ["2024-01-31"],
            "pred": [0.05],
        })
        result = build_ml_prediction_signal(
            df,
            asset_id_col="permno",
            date_col="yyyymm",
            prediction_col="pred",
        )
        assert result.loc[0, "asset_id"] == "10001"

    def test_empty_prediction_panel_raises(self):
        df = pd.DataFrame(columns=["asset_id", "date", "predicted_return"])
        with pytest.raises(ValueError, match="empty"):
            build_ml_prediction_signal(df)

    def test_no_valid_dates_after_parsing_raises(self):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["not_a_date"],
            "predicted_return": [0.05],
        })
        with pytest.raises(ValueError, match="no valid dates"):
            build_ml_prediction_signal(df)

    def test_all_nan_scores_date_is_neutral(self):
        df = pd.DataFrame({
            "asset_id": ["A", "B"],
            "date": ["2024-01-31", "2024-01-31"],
            "predicted_return": [None, None],
        })
        result = build_ml_prediction_signal(df)
        assert len(result) == 2
        assert (result["direction"] == 0).all()
        assert (result["target_weight"] == 0.0).all()

    def test_constant_scores_all_neutral(self):
        df = pd.DataFrame({
            "asset_id": ["A", "B", "C"],
            "date": ["2024-01-31", "2024-01-31", "2024-01-31"],
            "predicted_return": [0.01, 0.01, 0.01],
        })
        result = build_ml_prediction_signal(df)
        assert len(result) == 3
        assert (result["direction"] == 0).all()
        assert (result["target_weight"] == 0.0).all()

    def test_one_valid_score_all_neutral(self):
        df = pd.DataFrame({
            "asset_id": ["A", "B", "C"],
            "date": ["2024-01-31", "2024-01-31", "2024-01-31"],
            "predicted_return": [0.01, None, None],
        })
        result = build_ml_prediction_signal(df)
        assert len(result) == 3
        assert (result["direction"] == 0).all()
        assert (result["target_weight"] == 0.0).all()

    def test_constant_and_dispersed_dates(self):
        df = pd.DataFrame({
            "asset_id": ["A", "B", "A", "B", "C", "D", "E"],
            "date": ["2024-01-31", "2024-01-31", "2024-02-29", "2024-02-29", "2024-02-29", "2024-02-29", "2024-02-29"],
            "predicted_return": [0.01, 0.01, 0.10, 0.05, 0.01, -0.05, -0.10],
        })
        result = build_ml_prediction_signal(df, long_quantile=0.8, short_quantile=0.2)

        jan = result[result["datetime"] == pd.Timestamp("2024-01-31")]
        assert (jan["direction"] == 0).all()
        assert (jan["target_weight"] == 0.0).all()

        feb = result[result["datetime"] == pd.Timestamp("2024-02-29")]
        assert set(feb["direction"].unique()) == {-1, 0, 1}

    def test_dispersed_scores_still_produce_long_short_neutral(self):
        df = pd.DataFrame({
            "asset_id": ["A", "B", "C", "D", "E"],
            "date": ["2024-01-31"] * 5,
            "predicted_return": [0.10, 0.05, 0.01, -0.05, -0.10],
        })
        result = build_ml_prediction_signal(df, long_quantile=0.8, short_quantile=0.2)
        directions = set(result["direction"].unique())
        assert directions == {-1, 0, 1}

    def test_output_is_deterministic(self):
        df = pd.read_csv(PREDICTIONS_CSV)
        result1 = build_ml_prediction_signal(df)
        result2 = build_ml_prediction_signal(df)
        pd.testing.assert_frame_equal(result1, result2)

    def test_load_prediction_panel_rejects_excel(self):
        with pytest.raises(ValueError, match="Unsupported prediction file suffix"):
            load_prediction_panel(Path("data.xls"))


class TestCliBuildMlSignal:
    def test_cli_writes_csv_output(self, tmp_path):
        output = tmp_path / "ml_signal.csv"
        run_cli(
            "build-ml-signal",
            "--predictions", str(PREDICTIONS_CSV),
            "--output", str(output),
            "--asset-id-col", "asset_id",
            "--date-col", "date",
            "--prediction-col", "predicted_return",
            "--long-quantile", "0.8",
            "--short-quantile", "0.2",
        )
        assert output.exists()
        result = pd.read_csv(output)
        assert list(result.columns) == list(ML_SIGNAL_SIGNAL_COLUMNS)
        assert len(result) > 0

    def test_cli_writes_parquet_output(self, tmp_path):
        output = tmp_path / "ml_signal.parquet"
        run_cli(
            "build-ml-signal",
            "--predictions", str(PREDICTIONS_CSV),
            "--output", str(output),
            "--long-quantile", "0.8",
            "--short-quantile", "0.2",
        )
        assert output.exists()
        result = pd.read_parquet(output)
        assert list(result.columns) == list(ML_SIGNAL_SIGNAL_COLUMNS)
        assert len(result) > 0

    def test_cli_with_custom_columns(self, tmp_path):
        output = tmp_path / "signal.csv"
        run_cli(
            "build-ml-signal",
            "--predictions", str(PREDICTIONS_CSV),
            "--output", str(output),
            "--asset-id-col", "asset_id",
            "--date-col", "date",
            "--prediction-col", "predicted_return",
            "--signal-name", "ml_score",
            "--source", "TestML",
            "--long-quantile", "0.8",
            "--short-quantile", "0.2",
            "--gross-long-weight", "2.0",
            "--gross-short-weight", "-1.5",
        )
        result = pd.read_csv(output)
        assert (result["signal_name"] == "ml_score").all()
        assert (result["source"] == "TestML").all()

    def test_cli_is_deterministic(self, tmp_path):
        output1 = tmp_path / "run1.csv"
        output2 = tmp_path / "run2.csv"
        args = [
            "build-ml-signal",
            "--predictions", str(PREDICTIONS_CSV),
            "--long-quantile", "0.8",
            "--short-quantile", "0.2",
        ]
        run_cli(*args, "--output", str(output1))
        run_cli(*args, "--output", str(output2))
        result1 = pd.read_csv(output1)
        result2 = pd.read_csv(output2)
        pd.testing.assert_frame_equal(result1, result2)

    def test_cli_with_symbol_col(self, tmp_path):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-31"],
            "predicted_return": [0.05],
            "ticker": ["SYM"],
        })
        predictions = tmp_path / "pred.csv"
        df.to_csv(predictions, index=False)
        output = tmp_path / "signal.csv"
        run_cli(
            "build-ml-signal",
            "--predictions", str(predictions),
            "--output", str(output),
            "--symbol-col", "ticker",
            "--long-quantile", "0.8",
            "--short-quantile", "0.2",
        )
        result = pd.read_csv(output)
        assert result.loc[0, "symbol"] == "SYM"

    def test_cli_with_available_at_col(self, tmp_path):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-15"],
            "predicted_return": [0.05],
            "avail": ["2024-02-01"],
        })
        predictions = tmp_path / "pred.csv"
        df.to_csv(predictions, index=False)
        output = tmp_path / "signal.csv"
        run_cli(
            "build-ml-signal",
            "--predictions", str(predictions),
            "--output", str(output),
            "--available-at-col", "avail",
            "--long-quantile", "0.8",
            "--short-quantile", "0.2",
        )
        result = pd.read_csv(output)
        assert str(result.loc[0, "available_at"])[:10] == "2024-02-29"


def run_cli(*args: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alphaforge.cli", *args],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    if result.returncode != 0:
        raise RuntimeError(f"CLI failed with stderr:\n{result.stderr}\nstdout:\n{result.stdout}")
