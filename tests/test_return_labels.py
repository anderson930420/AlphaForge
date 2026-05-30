from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.return_labels import (
    build_forward_return_labels,
    join_features_with_return_labels,
    load_return_panel,
)


FIXTURES = Path(__file__).parent / "fixtures" / "return_labels"


class TestLoadReturnPanel:
    def test_csv_input(self):
        df = load_return_panel(FIXTURES / "monthly_returns.csv")
        assert list(df.columns) == ["asset_id", "date", "ret"]
        assert len(df) == 8

    def test_parquet_input(self):
        df = load_return_panel(FIXTURES / "monthly_returns.parquet")
        assert list(df.columns) == ["asset_id", "date", "ret"]
        assert len(df) == 8

    def test_unsupported_format_raises(self):
        with pytest.raises(ValueError, match="Unsupported file format"):
            load_return_panel(FIXTURES / "monthly_returns.txt")


class TestBuildForwardReturnLabels:
    def test_one_month_horizon_calendar_month_end(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A"],
            "date": ["2024-01-31", "2024-02-29", "2024-03-31"],
            "ret": [0.02, -0.01, 0.03],
        })
        result = build_forward_return_labels(df, horizon_months=1)
        assert len(result) == 2
        jan_row = result[result["date"] == pd.Timestamp("2024-01-31")].iloc[0]
        assert jan_row["target_date"] == pd.Timestamp("2024-02-29")
        assert jan_row["ret_fwd_1m"] == -0.01

    def test_missing_month_does_not_use_next_observed_row(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A"],
            "date": ["2024-01-31", "2024-02-29", "2024-03-31"],
            "ret": [0.02, -0.01, 0.03],
        })
        result = build_forward_return_labels(df, horizon_months=1)
        jan_row = result[result["date"] == pd.Timestamp("2024-01-31")].iloc[0]
        assert jan_row["target_date"] == pd.Timestamp("2024-02-29")
        assert jan_row["ret_fwd_1m"] == -0.01
        feb_row = result[result["date"] == pd.Timestamp("2024-02-29")].iloc[0]
        assert feb_row["target_date"] == pd.Timestamp("2024-03-31")
        assert feb_row["ret_fwd_1m"] == 0.03

    def test_multiple_assets_independent(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A", "B", "B", "B"],
            "date": ["2024-01-31", "2024-02-29", "2024-03-31"] * 2,
            "ret": [0.02, -0.01, 0.03, 0.01, -0.02, 0.015],
        })
        result = build_forward_return_labels(df, horizon_months=1)
        a_rows = result[result["asset_id"] == "A"]
        b_rows = result[result["asset_id"] == "B"]
        assert len(a_rows) == 2
        assert len(b_rows) == 2

    def test_last_month_no_fake_future_label(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A"],
            "date": ["2024-01-31", "2024-02-29", "2024-03-31"],
            "ret": [0.02, -0.01, 0.03],
        })
        result = build_forward_return_labels(df, horizon_months=1)
        assert len(result) == 2
        assert all(result["target_date"] <= pd.Timestamp("2024-03-31"))

    def test_delisting_return_combines_correctly(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A"],
            "date": ["2024-01-31", "2024-02-29"],
            "ret": [0.02, -0.01],
            "dlret": [0.005, 0.0],
        })
        result = build_forward_return_labels(df, horizon_months=1, delisting_return_col="dlret")
        jan_row = result[result["date"] == pd.Timestamp("2024-01-31")].iloc[0]
        assert abs(jan_row["ret_fwd_1m"] - (-0.01)) < 1e-10

    def test_missing_ret_present_dlret(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A"],
            "date": ["2024-01-31", "2024-02-29"],
            "ret": [float("nan"), -0.01],
            "dlret": [0.005, 0.0],
        })
        result = build_forward_return_labels(df, horizon_months=1, delisting_return_col="dlret")
        jan_row = result[result["date"] == pd.Timestamp("2024-01-31")].iloc[0]
        assert abs(jan_row["ret_fwd_1m"] - (-0.01)) < 1e-10

    def test_missing_both_ret_and_dlret_drops_row(self):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-31"],
            "ret": [float("nan")],
            "dlret": [float("nan")],
        })
        result = build_forward_return_labels(df, horizon_months=1, delisting_return_col="dlret")
        assert len(result) == 0

    def test_missing_required_columns_raises(self):
        df = pd.DataFrame({"asset_id": ["A"], "date": ["2024-01-31"]})
        with pytest.raises(ValueError, match="Missing required columns"):
            build_forward_return_labels(df)

    def test_horizon_months_less_than_one_raises(self):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-31"],
            "ret": [0.02],
        })
        with pytest.raises(ValueError, match="horizon_months must be >= 1"):
            build_forward_return_labels(df, horizon_months=0)

    def test_empty_panel_raises(self):
        df = pd.DataFrame(columns=["asset_id", "date", "ret"])
        with pytest.raises(ValueError, match="Empty return panel"):
            build_forward_return_labels(df)

    def test_output_schema(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A"],
            "date": ["2024-01-31", "2024-02-29", "2024-03-31"],
            "ret": [0.02, -0.01, 0.03],
        })
        result = build_forward_return_labels(df, horizon_months=1)
        assert set(result.columns) == {"asset_id", "date", "target_date", "horizon_months", "ret_fwd_1m", "source"}
        assert len(result) == 2

    def test_horizon_2_months(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A"],
            "date": ["2024-01-31", "2024-02-29", "2024-03-31"],
            "ret": [0.02, -0.01, 0.03],
        })
        result = build_forward_return_labels(df, horizon_months=2)
        jan_row = result[result["date"] == pd.Timestamp("2024-01-31")].iloc[0]
        assert jan_row["target_date"] == pd.Timestamp("2024-03-31")

    def test_deterministic_output(self):
        df1 = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-31"],
            "ret": [0.02],
        })
        df2 = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-31"],
            "ret": [0.02],
        })
        r1 = build_forward_return_labels(df1, horizon_months=1)
        r2 = build_forward_return_labels(df2, horizon_months=1)
        pd.testing.assert_frame_equal(r1, r2)

    def test_missing_month_jan_not_march_return(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A"],
            "date": ["2024-01-31", "2024-03-31"],
            "ret": [0.02, 0.03],
        })
        result = build_forward_return_labels(df, horizon_months=1)
        assert len(result) == 0

    def test_empty_returns_deterministic_schema(self):
        df = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-31"],
            "ret": [float("nan")],
        })
        result = build_forward_return_labels(df, horizon_months=1)
        assert list(result.columns) == ["asset_id", "date", "target_date", "horizon_months", "ret_fwd_1m", "source"]
        assert len(result) == 0

    def test_delisting_at_target_month_uses_dlret(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A"],
            "date": ["2024-01-31", "2024-02-29", "2024-03-31"],
            "ret": [0.02, float("nan"), float("nan")],
            "dlret": [0.005, 0.01, 0.01],
        })
        result = build_forward_return_labels(df, horizon_months=1, delisting_return_col="dlret")
        feb_row = result[result["date"] == pd.Timestamp("2024-02-29")].iloc[0]
        assert abs(feb_row["ret_fwd_1m"] - 0.01) < 1e-10

    def test_duplicate_target_month_uses_last_sorted_return_like_previous_lookup(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A"],
            "date": ["2024-01-31", "2024-02-29", "2024-02-29"],
            "ret": [0.02, -0.01, 0.04],
        })

        result = build_forward_return_labels(df, horizon_months=1)

        jan_row = result[result["date"] == pd.Timestamp("2024-01-31")].iloc[0]
        assert jan_row["ret_fwd_1m"] == 0.04

    def test_duplicate_source_month_rows_are_preserved_when_future_label_exists(self):
        df = pd.DataFrame({
            "asset_id": ["A", "A", "A"],
            "date": ["2024-01-31", "2024-01-31", "2024-02-29"],
            "ret": [0.02, 0.03, -0.01],
        })

        result = build_forward_return_labels(df, horizon_months=1)

        jan_rows = result[result["date"] == pd.Timestamp("2024-01-31")]
        assert len(jan_rows) == 2
        assert set(jan_rows["ret_fwd_1m"]) == {-0.01}


class TestJoinFeaturesWithReturnLabels:
    def test_join_features_with_labels(self):
        features = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-31"],
            "Mom12m": [0.1],
        })
        labels = pd.DataFrame({
            "asset_id": ["A"],
            "date": ["2024-01-31"],
            "target_date": ["2024-02-29"],
            "horizon_months": [1],
            "ret_fwd_1m": [-0.01],
            "source": ["local_returns"],
        })
        result = join_features_with_return_labels(features, labels)
        assert len(result) == 1
        assert "Mom12m" in result.columns
        assert "ret_fwd_1m" in result.columns

    def test_no_orig_date_columns_in_output(self):
        features = pd.DataFrame({
            "asset_id": [1],
            "date": ["2024-01-31"],
            "Mom12m": [0.1],
        })
        labels = pd.DataFrame({
            "asset_id": ["1"],
            "date": ["2024-01-31"],
            "target_date": ["2024-02-29"],
            "horizon_months": [1],
            "ret_fwd_1m": [-0.01],
            "source": ["local_returns"],
        })
        result = join_features_with_return_labels(features, labels)
        leaky = [c for c in result.columns if "_orig_date" in c]
        assert leaky == [], f"Leaky columns found: {leaky}"

    def test_int_string_asset_id_join(self):
        features = pd.DataFrame({
            "asset_id": [1, 2],
            "date": ["2024-01-31", "2024-01-31"],
            "Mom12m": [0.1, 0.2],
        })
        labels = pd.DataFrame({
            "asset_id": ["1", "2"],
            "date": ["2024-01-31", "2024-01-31"],
            "target_date": ["2024-02-29", "2024-02-29"],
            "horizon_months": [1, 1],
            "ret_fwd_1m": [-0.01, -0.02],
            "source": ["local_returns", "local_returns"],
        })
        result = join_features_with_return_labels(features, labels)
        assert len(result) == 2


class TestCLI:
    def test_cli_help(self):
        result = subprocess.run(
            ["python3", "-m", "alphaforge.cli", "build-return-labels", "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "build-return-labels" in result.stdout
