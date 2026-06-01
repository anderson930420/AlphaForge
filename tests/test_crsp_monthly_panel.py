from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.crsp_monthly_panel import (
    CRSP_MONTHLY_PANEL_COLUMNS,
    build_crsp_monthly_panel_qc,
    load_crsp_monthly_panel,
    validate_crsp_monthly_panel,
)


ROOT = Path(__file__).resolve().parents[1]


def _panel_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": "2024-01-31",
                "asset_id": "A",
                "permno": 10001,
                "permco": 20001,
                "ticker": "AAA",
                "cusip": "11111111",
                "ncusip": "11111111",
                "exchcd": 1,
                "shrcd": 10,
                "siccd": 1234,
                "price": 10.0,
                "ret": 0.01,
                "retx": 0.01,
                "dlret": None,
                "volume": 1000.0,
                "shares_out": 100.0,
                "market_cap": 1000.0,
                "lag_market_cap": 990.0,
                "total_ret": 0.01,
                "is_common_share": True,
                "is_primary_us_exchange": True,
                "daily_obs_count": 20,
                "first_trading_date": "2020-01-01",
                "last_trading_date": "2024-01-31",
            },
            {
                "date": "2024-02-29",
                "asset_id": "A",
                "permno": 10001,
                "permco": 20001,
                "ticker": "AAA",
                "cusip": "11111111",
                "ncusip": "11111111",
                "exchcd": 1,
                "shrcd": 10,
                "siccd": 1234,
                "price": 11.0,
                "ret": float("nan"),
                "retx": 0.02,
                "dlret": None,
                "volume": 1100.0,
                "shares_out": 100.0,
                "market_cap": 1100.0,
                "lag_market_cap": 1000.0,
                "total_ret": float("nan"),
                "is_common_share": True,
                "is_primary_us_exchange": False,
                "daily_obs_count": 18,
                "first_trading_date": "2020-01-01",
                "last_trading_date": "2024-02-29",
            },
            {
                "date": "2024-01-31",
                "asset_id": "B",
                "permno": 10002,
                "permco": 20002,
                "ticker": "BBB",
                "cusip": "22222222",
                "ncusip": "22222222",
                "exchcd": 3,
                "shrcd": 11,
                "siccd": 5678,
                "price": 20.0,
                "ret": 0.03,
                "retx": 0.03,
                "dlret": None,
                "volume": 2000.0,
                "shares_out": 200.0,
                "market_cap": 4000.0,
                "lag_market_cap": 3900.0,
                "total_ret": 0.03,
                "is_common_share": False,
                "is_primary_us_exchange": True,
                "daily_obs_count": 21,
                "first_trading_date": "2019-05-01",
                "last_trading_date": "2024-01-31",
            },
            {
                "date": "2024-02-29",
                "asset_id": "B",
                "permno": 10002,
                "permco": 20002,
                "ticker": "BBB",
                "cusip": "22222222",
                "ncusip": "22222222",
                "exchcd": 3,
                "shrcd": 11,
                "siccd": 5678,
                "price": 21.0,
                "ret": 0.04,
                "retx": 0.04,
                "dlret": None,
                "volume": 2100.0,
                "shares_out": 200.0,
                "market_cap": 4200.0,
                "lag_market_cap": 4000.0,
                "total_ret": 0.04,
                "is_common_share": False,
                "is_primary_us_exchange": True,
                "daily_obs_count": 19,
                "first_trading_date": "2019-05-01",
                "last_trading_date": "2024-02-29",
            },
        ]
    )


def _write_panel(tmp_path: Path, frame: pd.DataFrame | None = None) -> Path:
    path = tmp_path / "crsp_monthly.parquet"
    (frame if frame is not None else _panel_frame()).to_parquet(path, index=False)
    return path


def test_load_crsp_monthly_panel_returns_canonical_columns_and_sorted_rows(tmp_path: Path) -> None:
    path = _write_panel(tmp_path)

    loaded = load_crsp_monthly_panel(path)

    assert loaded.columns.tolist() == CRSP_MONTHLY_PANEL_COLUMNS
    assert loaded[["asset_id", "date"]].astype(str).values.tolist() == [
        ["A", "2024-01-31"],
        ["A", "2024-02-29"],
        ["B", "2024-01-31"],
        ["B", "2024-02-29"],
    ]


def test_validate_crsp_monthly_panel_rejects_missing_required_columns() -> None:
    raw = _panel_frame().drop(columns=["market_cap"])

    with pytest.raises(ValueError, match="Missing required CRSP monthly panel columns"):
        validate_crsp_monthly_panel(raw)


def test_validate_crsp_monthly_panel_rejects_duplicate_asset_date_rows() -> None:
    raw = pd.concat([_panel_frame(), _panel_frame().iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate asset_id/date rows are not allowed"):
        validate_crsp_monthly_panel(raw)


def test_load_crsp_monthly_panel_applies_date_filters(tmp_path: Path) -> None:
    path = _write_panel(tmp_path)

    loaded = load_crsp_monthly_panel(path, start_date="2024-02-01", end_date="2024-02-29")

    assert loaded["date"].dt.strftime("%Y-%m-%d").tolist() == ["2024-02-29", "2024-02-29"]
    assert loaded["asset_id"].tolist() == ["A", "B"]


def test_load_crsp_monthly_panel_applies_common_share_filter(tmp_path: Path) -> None:
    path = _write_panel(tmp_path)

    loaded = load_crsp_monthly_panel(path, common_shares_only=True)

    assert loaded["asset_id"].tolist() == ["A", "A"]
    assert loaded["is_common_share"].tolist() == [True, True]


def test_load_crsp_monthly_panel_applies_primary_exchange_filter(tmp_path: Path) -> None:
    path = _write_panel(tmp_path)

    loaded = load_crsp_monthly_panel(path, primary_exchange_only=True)

    assert loaded["asset_id"].tolist() == ["A", "B", "B"]
    assert loaded["is_primary_us_exchange"].tolist() == [True, True, True]


def test_load_crsp_monthly_panel_honors_requested_columns_after_validation(tmp_path: Path) -> None:
    path = _write_panel(tmp_path)

    loaded = load_crsp_monthly_panel(path, columns=["asset_id", "date", "price"])

    assert loaded.columns.tolist() == ["asset_id", "date", "price"]
    assert loaded["asset_id"].tolist() == ["A", "A", "B", "B"]


def test_build_crsp_monthly_panel_qc_reports_expected_counts() -> None:
    qc = build_crsp_monthly_panel_qc(_panel_frame())

    assert qc["rows"] == 4
    assert qc["assets"] == 2
    assert qc["date_min"] == "2024-01-31"
    assert qc["date_max"] == "2024-02-29"
    assert qc["months"] == 2
    assert qc["duplicate_asset_date_rows"] == 0
    assert qc["missing_ret_ratio"] == pytest.approx(0.25)
    assert qc["missing_total_ret_ratio"] == pytest.approx(0.25)
    assert qc["missing_price_ratio"] == pytest.approx(0.0)
    assert qc["missing_market_cap_ratio"] == pytest.approx(0.0)
    assert qc["missing_lag_market_cap_ratio"] == pytest.approx(0.0)
    assert qc["common_share_rows"] == 2
    assert qc["primary_exchange_rows"] == 3
    assert qc["frequency"] == "monthly"


def test_inspect_crsp_monthly_panel_cli_prints_and_writes_qc_json(tmp_path: Path) -> None:
    input_path = _write_panel(tmp_path)
    qc_output = tmp_path / "qc" / "panel_qc.json"
    script_path = ROOT / "scripts" / "inspect_crsp_monthly_panel.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--input",
            str(input_path),
            "--qc-output",
            str(qc_output),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    stdout_qc = json.loads(result.stdout)
    file_qc = json.loads(qc_output.read_text(encoding="utf-8"))

    assert stdout_qc == file_qc
    assert stdout_qc["rows"] == 4
    assert stdout_qc["frequency"] == "monthly"
    assert "date_min" in stdout_qc
