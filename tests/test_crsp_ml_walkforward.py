from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.crsp_ml_walkforward import (
    WalkForwardWindow,
    build_walk_forward_qc,
    build_walk_forward_splits,
    generate_walk_forward_windows,
    split_dataset_for_window,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_crsp_ml_walk_forward_splits.py"


def _make_walkforward_dataset() -> pd.DataFrame:
    dates = pd.date_range("2000-01-31", "2012-12-31", freq="ME")
    assets = [
        ("A", 10001, "AAA"),
        ("B", 10002, "BBB"),
        ("C", 10003, "CCC"),
    ]
    rows: list[dict[str, object]] = []
    for month_index, date_value in enumerate(dates):
        for asset_index, (asset_id, permno, ticker) in enumerate(assets):
            base = month_index * 10 + asset_index
            price = 20.0 + base
            market_cap = 2000.0 + (base * 10.0)
            lag_market_cap = market_cap - 25.0
            volume = 1000.0 + (base * 5.0)
            shares_out = 100.0 + asset_index
            rows.append(
                {
                    "date": date_value,
                    "asset_id": asset_id,
                    "permno": permno,
                    "ticker": ticker,
                    "price": price,
                    "market_cap": market_cap,
                    "lag_market_cap": lag_market_cap,
                    "total_ret": 0.01 + (month_index * 0.0001) + (asset_index * 0.00001),
                    "mom12_1": 0.10 + (base * 0.001),
                    "mom6_1": 0.06 + (base * 0.001),
                    "mom3_1": 0.03 + (base * 0.001),
                    "ret1_0": 0.01 + (base * 0.0001),
                    "volatility_12m": 0.20 + (asset_index * 0.01),
                    "turnover": volume / shares_out,
                    "log_market_cap": math.log(lag_market_cap),
                    "log_price": math.log(price),
                    "forward_1m_total_ret": 0.02 + (month_index * 0.0001) + (asset_index * 0.00001),
                }
            )
    frame = pd.DataFrame(rows)
    frame = frame.sample(frac=1.0, random_state=7).reset_index(drop=True)
    return frame


class TestGenerateWalkForwardWindows:
    def test_creates_expected_rolling_windows(self) -> None:
        windows = generate_walk_forward_windows(
            date_min="2000-01-15",
            date_max="2012-12-31",
            first_train_start="2000-01-10",
            train_years=10,
            test_years=1,
            step_years=1,
        )

        assert windows == [
            WalkForwardWindow(
                window_id="train_2000-2009_test_2010",
                train_start=pd.Timestamp("2000-01-31"),
                train_end=pd.Timestamp("2009-12-31"),
                test_start=pd.Timestamp("2010-01-31"),
                test_end=pd.Timestamp("2010-12-31"),
            ),
            WalkForwardWindow(
                window_id="train_2001-2010_test_2011",
                train_start=pd.Timestamp("2001-01-31"),
                train_end=pd.Timestamp("2010-12-31"),
                test_start=pd.Timestamp("2011-01-31"),
                test_end=pd.Timestamp("2011-12-31"),
            ),
            WalkForwardWindow(
                window_id="train_2002-2011_test_2012",
                train_start=pd.Timestamp("2002-01-31"),
                train_end=pd.Timestamp("2011-12-31"),
                test_start=pd.Timestamp("2012-01-31"),
                test_end=pd.Timestamp("2012-12-31"),
            ),
        ]
        assert windows == generate_walk_forward_windows(
            date_min="2000-01-15",
            date_max="2012-12-31",
            first_train_start="2000-01-10",
            train_years=10,
            test_years=1,
            step_years=1,
        )

    @pytest.mark.parametrize(
        ("train_years", "test_years", "step_years", "message"),
        [
            (0, 1, 1, "train_years must be > 0"),
            (10, 0, 1, "test_years must be > 0"),
            (10, 1, 0, "step_years must be > 0"),
        ],
    )
    def test_rejects_invalid_year_arguments(
        self,
        train_years: int,
        test_years: int,
        step_years: int,
        message: str,
    ) -> None:
        with pytest.raises(ValueError, match=message):
            generate_walk_forward_windows(
                date_min="2000-01-31",
                date_max="2012-12-31",
                train_years=train_years,
                test_years=test_years,
                step_years=step_years,
            )


class TestSplitDatasetForWindow:
    def test_returns_expected_train_and_test_rows_without_mutating_input(self) -> None:
        dataset = _make_walkforward_dataset()
        original = dataset.copy(deep=True)
        window = generate_walk_forward_windows(
            date_min="2000-01-31",
            date_max="2012-12-31",
            train_years=10,
            test_years=1,
            step_years=1,
        )[0]

        train_df, test_df = split_dataset_for_window(dataset, window)

        pd.testing.assert_frame_equal(dataset, original)
        assert len(train_df) == 360
        assert len(test_df) == 36
        assert train_df["date"].min() == pd.Timestamp("2000-01-31")
        assert train_df["date"].max() == pd.Timestamp("2009-12-31")
        assert test_df["date"].min() == pd.Timestamp("2010-01-31")
        assert test_df["date"].max() == pd.Timestamp("2010-12-31")
        assert set(train_df["date"].unique()).isdisjoint(set(test_df["date"].unique()))
        assert list(zip(train_df["date"], train_df["asset_id"])) == sorted(
            zip(train_df["date"], train_df["asset_id"])
        )
        assert list(zip(test_df["date"], test_df["asset_id"])) == sorted(
            zip(test_df["date"], test_df["asset_id"])
        )

    @pytest.mark.parametrize(
        ("window", "message"),
        [
            (
                WalkForwardWindow(
                    window_id="empty-train",
                    train_start=pd.Timestamp("1990-01-31"),
                    train_end=pd.Timestamp("1999-12-31"),
                    test_start=pd.Timestamp("2000-01-31"),
                    test_end=pd.Timestamp("2000-12-31"),
                ),
                "Train split is empty",
            ),
            (
                WalkForwardWindow(
                    window_id="empty-test",
                    train_start=pd.Timestamp("2000-01-31"),
                    train_end=pd.Timestamp("2009-12-31"),
                    test_start=pd.Timestamp("2013-01-31"),
                    test_end=pd.Timestamp("2013-12-31"),
                ),
                "Test split is empty",
            ),
        ],
    )
    def test_raises_on_empty_train_or_test_split(self, window: WalkForwardWindow, message: str) -> None:
        dataset = _make_walkforward_dataset()

        with pytest.raises(ValueError, match=message):
            split_dataset_for_window(dataset, window)


class TestBuildWalkForwardSplits:
    def test_respects_start_and_end_date_filters(self) -> None:
        dataset = _make_walkforward_dataset()

        splits = build_walk_forward_splits(
            dataset,
            train_years=10,
            test_years=1,
            step_years=1,
            start_date="2001-01-31",
            end_date="2012-12-31",
        )

        assert [window.window_id for window, _, _ in splits] == [
            "train_2001-2010_test_2011",
            "train_2002-2011_test_2012",
        ]
        assert splits[0][1]["date"].min() == pd.Timestamp("2001-01-31")
        assert splits[-1][2]["date"].max() == pd.Timestamp("2012-12-31")

    def test_rejects_duplicate_asset_date_rows(self) -> None:
        dataset = pd.concat([_make_walkforward_dataset(), _make_walkforward_dataset().iloc[[0]]], ignore_index=True)

        with pytest.raises(ValueError, match="duplicate asset_id/date rows are not allowed"):
            build_walk_forward_splits(dataset)


class TestBuildWalkForwardQc:
    def test_reports_expected_counts_and_months(self) -> None:
        dataset = _make_walkforward_dataset()
        splits = build_walk_forward_splits(dataset)

        qc = build_walk_forward_qc(splits)

        assert qc["windows"] == 3
        assert qc["total_train_rows"] == 1080
        assert qc["total_test_rows"] == 108
        assert qc["first_train_start"] == "2000-01-31"
        assert qc["last_test_end"] == "2012-12-31"
        assert qc["train_years"] == 10
        assert qc["test_years"] == 1
        assert qc["step_years"] == 1
        assert len(qc["per_window"]) == 3

        first_window = qc["per_window"][0]
        assert first_window["window_id"] == "train_2000-2009_test_2010"
        assert first_window["train_rows"] == 360
        assert first_window["test_rows"] == 36
        assert first_window["train_assets"] == 3
        assert first_window["test_assets"] == 3
        assert first_window["train_months"] == 120
        assert first_window["test_months"] == 12
        assert first_window["train_duplicate_asset_date_rows"] == 0
        assert first_window["test_duplicate_asset_date_rows"] == 0


class TestBuildCrspMlWalkForwardSplitsCli:
    def test_cli_smoke_writes_train_test_parquet_qc_and_manifest(self, tmp_path: Path) -> None:
        input_path = tmp_path / "crsp_ml_dataset.parquet"
        output_dir = tmp_path / "walkforward"
        qc_output = tmp_path / "walkforward" / "walk_forward_qc.json"
        manifest_output = tmp_path / "walkforward" / "walk_forward_manifest.json"
        _make_walkforward_dataset().to_parquet(input_path, index=False)

        env = os.environ.copy()
        env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--input",
                str(input_path),
                "--output-dir",
                str(output_dir),
                "--start-date",
                "2001-01-31",
                "--end-date",
                "2012-12-31",
                "--train-years",
                "10",
                "--test-years",
                "1",
                "--step-years",
                "1",
                "--qc-output",
                str(qc_output),
                "--manifest-output",
                str(manifest_output),
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0, result.stderr
        assert qc_output.exists()
        assert manifest_output.exists()

        stdout_qc = json.loads(result.stdout)
        file_qc = json.loads(qc_output.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_output.read_text(encoding="utf-8"))

        assert stdout_qc == file_qc
        assert stdout_qc["status"] == "ok"
        assert stdout_qc["windows"] == 2
        assert stdout_qc["total_train_rows"] == 720
        assert stdout_qc["total_test_rows"] == 72
        assert manifest["status"] == "ok"
        assert manifest["window_count"] == 2
        assert len(manifest["windows"]) == 2

        first_window_dir = output_dir / "train_2001-2010_test_2011"
        second_window_dir = output_dir / "train_2002-2011_test_2012"
        assert (first_window_dir / "train.parquet").exists()
        assert (first_window_dir / "test.parquet").exists()
        assert (second_window_dir / "train.parquet").exists()
        assert (second_window_dir / "test.parquet").exists()

        train_df = pd.read_parquet(first_window_dir / "train.parquet")
        test_df = pd.read_parquet(first_window_dir / "test.parquet")
        assert len(train_df) == 360
        assert len(test_df) == 36
        assert train_df["date"].min() == pd.Timestamp("2001-01-31")
        assert test_df["date"].max() == pd.Timestamp("2011-12-31")
