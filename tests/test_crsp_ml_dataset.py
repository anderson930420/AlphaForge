from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alphaforge.crsp_ml_dataset import (
    CRSP_ML_FEATURE_COLUMNS,
    CRSP_ML_LABEL_COLUMN,
    build_crsp_ml_dataset,
    build_crsp_ml_dataset_qc,
    build_crsp_ml_features,
    add_forward_return_label,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_crsp_ml_dataset.py"


def _make_asset_rows(
    asset_id: str,
    permno: int,
    ticker: str,
    returns: list[float],
    *,
    common: bool = True,
    primary: bool = True,
    price_start: float = 20.0,
    market_cap_start: float = 2000.0,
    lag_market_cap_start: float = 1900.0,
    volume_start: float = 1000.0,
    shares_out_start: float = 100.0,
    missing_price_indices: set[int] | None = None,
) -> list[dict[str, object]]:
    missing_price_indices = missing_price_indices or set()
    dates = pd.date_range("2020-01-31", periods=len(returns), freq="ME")
    rows: list[dict[str, object]] = []
    for index, (date_value, total_ret) in enumerate(zip(dates, returns)):
        price = price_start + index
        volume = volume_start + (index * 100.0)
        shares_out = shares_out_start + (index * 10.0)
        market_cap = market_cap_start + (index * 100.0)
        lag_market_cap = lag_market_cap_start + (index * 100.0)
        if index in missing_price_indices:
            price = np.nan

        rows.append(
            {
                "date": date_value,
                "asset_id": asset_id,
                "permno": permno,
                "permco": permno + 1000,
                "ticker": ticker,
                "cusip": f"{permno:08d}",
                "ncusip": f"{permno:08d}",
                "exchcd": 1,
                "shrcd": 10,
                "siccd": 1234,
                "price": price,
                "ret": total_ret,
                "retx": total_ret,
                "dlret": None,
                "volume": volume,
                "shares_out": shares_out,
                "market_cap": market_cap,
                "lag_market_cap": lag_market_cap,
                "total_ret": total_ret,
                "is_common_share": common,
                "is_primary_us_exchange": primary,
                "daily_obs_count": 20,
                "first_trading_date": "2010-01-31",
                "last_trading_date": date_value,
            }
        )
    return rows


def _make_panel(*, missing_price_indices: set[int] | None = None) -> pd.DataFrame:
    a_returns = [0.01] * 11 + [0.50, 0.02, 0.03, 0.04]
    b_returns = [0.02] * 11 + [0.40, 0.05, 0.06, 0.07]
    rows: list[dict[str, object]] = []
    rows.extend(
        _make_asset_rows(
            "A",
            10001,
            "AAA",
            a_returns,
            common=True,
            primary=True,
            missing_price_indices=missing_price_indices,
        )
    )
    rows.extend(_make_asset_rows("B", 10002, "BBB", b_returns, common=True, primary=True))
    return pd.DataFrame(rows)


class TestBuildCrspMlFeatures:
    def test_feature_windows_use_correct_ranges(self) -> None:
        panel = _make_panel()

        features = build_crsp_ml_features(panel, min_mom_obs=8)
        target = features.loc[
            (features["asset_id"] == "A") & (features["date"] == pd.Timestamp("2021-01-31"))
        ].iloc[0]

        assert list(features.columns) == [
            "date",
            "asset_id",
            "permno",
            "ticker",
            "price",
            "market_cap",
            "lag_market_cap",
            "total_ret",
            "mom12_1",
            "mom6_1",
            "mom3_1",
            "ret1_0",
            "volatility_12m",
            "turnover",
            "log_market_cap",
            "log_price",
        ]
        assert target["mom12_1"] == pytest.approx((1.01 ** 11) - 1.0)
        assert target["mom6_1"] == pytest.approx((1.01 ** 5) - 1.0)
        assert target["mom3_1"] == pytest.approx((1.01 ** 2) - 1.0)
        assert target["ret1_0"] == pytest.approx(0.02)
        expected_vol = pd.Series([0.01] * 10 + [0.50, 0.02]).std(ddof=1)
        assert target["volatility_12m"] == pytest.approx(expected_vol)
        assert target["turnover"] == pytest.approx(10.0)
        assert target["log_market_cap"] == pytest.approx(np.log(3100.0))
        assert target["log_price"] == pytest.approx(np.log(32.0))

    def test_features_do_not_see_future_returns(self) -> None:
        panel_a = _make_panel()
        panel_b = _make_panel()
        panel_b.loc[(panel_b["asset_id"] == "A") & (panel_b["date"] >= pd.Timestamp("2021-02-28")), "total_ret"] = [
            0.99,
            0.88,
        ]
        panel_b.loc[(panel_b["asset_id"] == "A") & (panel_b["date"] >= pd.Timestamp("2021-02-28")), "ret"] = [
            0.99,
            0.88,
        ]
        panel_b.loc[(panel_b["asset_id"] == "A") & (panel_b["date"] >= pd.Timestamp("2021-02-28")), "retx"] = [
            0.99,
            0.88,
        ]

        features_a = build_crsp_ml_features(panel_a, min_mom_obs=8)
        features_b = build_crsp_ml_features(panel_b, min_mom_obs=8)

        row_a = features_a.loc[
            (features_a["asset_id"] == "A") & (features_a["date"] == pd.Timestamp("2021-01-31"))
        ].iloc[0]
        row_b = features_b.loc[
            (features_b["asset_id"] == "A") & (features_b["date"] == pd.Timestamp("2021-01-31"))
        ].iloc[0]

        for column in [
            "mom12_1",
            "mom6_1",
            "mom3_1",
            "ret1_0",
            "volatility_12m",
            "turnover",
            "log_market_cap",
            "log_price",
        ]:
            assert row_b[column] == pytest.approx(row_a[column])


class TestForwardReturnLabel:
    def test_forward_label_uses_next_month_and_leaves_last_month_missing(self) -> None:
        panel = _make_panel()
        features = build_crsp_ml_features(panel, min_mom_obs=8)
        labeled = add_forward_return_label(features)

        target = labeled.loc[
            (labeled["asset_id"] == "A") & (labeled["date"] == pd.Timestamp("2021-01-31"))
        ].iloc[0]
        last_row = labeled.loc[
            (labeled["asset_id"] == "A") & (labeled["date"] == pd.Timestamp("2021-03-31"))
        ].iloc[0]

        assert target[CRSP_ML_LABEL_COLUMN] == pytest.approx(0.03)
        assert pd.isna(last_row[CRSP_ML_LABEL_COLUMN])

    def test_forward_label_is_asset_specific(self) -> None:
        panel = _make_panel()
        features = build_crsp_ml_features(panel, min_mom_obs=8)
        labeled = add_forward_return_label(features)

        a_label = labeled.loc[
            (labeled["asset_id"] == "A") & (labeled["date"] == pd.Timestamp("2021-01-31"))
        ].iloc[0][CRSP_ML_LABEL_COLUMN]
        b_label = labeled.loc[
            (labeled["asset_id"] == "B") & (labeled["date"] == pd.Timestamp("2021-01-31"))
        ].iloc[0][CRSP_ML_LABEL_COLUMN]

        assert a_label == pytest.approx(0.03)
        assert b_label == pytest.approx(0.06)


class TestBuildCrspMlDataset:
    def test_drop_missing_label_and_features(self) -> None:
        panel = _make_panel(missing_price_indices={12})

        full = build_crsp_ml_dataset(
            panel,
            min_mom_obs=8,
            drop_missing_label=False,
            drop_missing_features=False,
        )
        label_dropped = build_crsp_ml_dataset(
            panel,
            min_mom_obs=8,
            drop_missing_label=True,
            drop_missing_features=False,
        )
        feature_dropped = build_crsp_ml_dataset(
            panel,
            min_mom_obs=8,
            drop_missing_label=False,
            drop_missing_features=True,
        )

        assert len(label_dropped) == len(full) - 2
        assert not label_dropped[CRSP_ML_LABEL_COLUMN].isna().any()
        assert not feature_dropped[CRSP_ML_FEATURE_COLUMNS].isna().any().any()
        assert not (
            (feature_dropped["asset_id"] == "A") & (feature_dropped["date"] == pd.Timestamp("2021-01-31"))
        ).any()

    def test_dataset_sorting_and_qc_fields_are_correct(self) -> None:
        panel = _make_panel()
        dataset = build_crsp_ml_dataset(
            panel,
            min_mom_obs=8,
            drop_missing_label=True,
            drop_missing_features=False,
        )

        pairs = list(zip(dataset["date"], dataset["asset_id"]))
        assert pairs == sorted(pairs)
        assert not dataset[["asset_id", "date"]].duplicated().any()

        qc = build_crsp_ml_dataset_qc(dataset)
        assert qc["rows"] == len(dataset)
        assert qc["assets"] == 2
        assert qc["date_min"] == "2020-01-31"
        assert qc["date_max"] == "2021-02-28"
        assert qc["months"] == 14
        assert qc["feature_columns"] == CRSP_ML_FEATURE_COLUMNS
        assert qc["label_column"] == CRSP_ML_LABEL_COLUMN
        assert qc["missing_label_ratio"] == pytest.approx(0.0)
        assert qc["missing_log_price_ratio"] == pytest.approx(0.0)
        assert qc["duplicate_asset_date_rows"] == 0
        assert qc["frequency"] == "monthly"

    def test_cli_smoke_writes_dataset_and_qc(self, tmp_path: Path) -> None:
        input_path = tmp_path / "crsp_monthly.parquet"
        output_path = tmp_path / "dataset" / "crsp_ml_dataset.parquet"
        qc_output_path = tmp_path / "dataset" / "crsp_ml_dataset_qc.json"
        _make_panel().to_parquet(input_path, index=False)

        env = os.environ.copy()
        env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--input",
                str(input_path),
                "--output",
                str(output_path),
                "--qc-output",
                str(qc_output_path),
                "--start-date",
                "2021-01-31",
                "--end-date",
                "2021-02-28",
                "--min-mom-obs",
                "8",
                "--drop-missing-label",
                "--common-shares-only",
                "--primary-exchange-only",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0, result.stderr
        assert output_path.exists()
        assert qc_output_path.exists()

        stdout_qc = json.loads(result.stdout)
        file_qc = json.loads(qc_output_path.read_text(encoding="utf-8"))
        assert stdout_qc == file_qc
        assert stdout_qc["status"] == "ok"
        assert stdout_qc["rows"] == 4
        assert stdout_qc["assets"] == 2
        assert stdout_qc["date_min"] == "2021-01-31"
        assert stdout_qc["date_max"] == "2021-02-28"

        dataset = pd.read_parquet(output_path)
        assert list(dataset.columns) == [
            "date",
            "asset_id",
            "permno",
            "ticker",
            "price",
            "market_cap",
            "lag_market_cap",
            "total_ret",
            "mom12_1",
            "mom6_1",
            "mom3_1",
            "ret1_0",
            "volatility_12m",
            "turnover",
            "log_market_cap",
            "log_price",
            CRSP_ML_LABEL_COLUMN,
        ]
        assert len(dataset) == 4
        assert dataset["date"].tolist() == [
            pd.Timestamp("2021-01-31"),
            pd.Timestamp("2021-01-31"),
            pd.Timestamp("2021-02-28"),
            pd.Timestamp("2021-02-28"),
        ]
        assert not dataset["mom12_1"].isna().any()
        assert not dataset["volatility_12m"].isna().any()
