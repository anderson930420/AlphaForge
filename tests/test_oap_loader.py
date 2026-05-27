from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.oap_factor_contract import load_oap_factor_contract
from alphaforge.oap_loader import (
    OAP_FACTOR_FRAME_COLUMNS,
    OAPLoaderError,
    load_oap_factor_frame,
    normalize_oap_factor_frame,
)


CONTRACT_FIXTURE = Path("tests/fixtures/oap_factor_contracts/mom12m_threshold.yaml")


def _contract():
    return load_oap_factor_contract(CONTRACT_FIXTURE)


def _raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2024-01-31", "2024-01-31", "2024-02-29"],
            "permno": ["10001", "10002", "10001"],
            "symbol": ["AAA", "BBB", "AAA"],
            "Mom12m": [0.12, -0.05, 0.2],
        }
    )


def test_normalize_oap_factor_frame_uses_contract_columns_and_next_month_policy() -> None:
    normalized = normalize_oap_factor_frame(_raw_frame(), _contract())

    assert normalized.columns.tolist() == list(OAP_FACTOR_FRAME_COLUMNS)
    assert normalized["datetime"].astype(str).tolist() == ["2024-01-31", "2024-01-31", "2024-02-29"]
    assert normalized["available_at"].astype(str).tolist() == ["2024-02-01", "2024-02-01", "2024-03-01"]
    assert normalized["symbol"].tolist() == ["AAA", "BBB", "AAA"]
    assert normalized["asset_id"].tolist() == ["10001", "10002", "10001"]
    assert normalized["factor_name"].unique().tolist() == ["Mom12m"]
    assert normalized["factor_value"].tolist() == [0.12, -0.05, 0.2]
    assert normalized["source"].unique().tolist() == ["open_asset_pricing:jkp"]


def test_load_oap_factor_frame_reads_local_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "mom12m.csv"
    _raw_frame().to_csv(csv_path, index=False)

    normalized = load_oap_factor_frame(csv_path, _contract())

    assert len(normalized) == 3
    assert normalized["factor_value"].tolist() == [0.12, -0.05, 0.2]


def test_loader_falls_back_to_asset_id_when_symbol_column_is_absent() -> None:
    raw = _raw_frame().drop(columns=["symbol"])

    normalized = normalize_oap_factor_frame(raw, _contract())

    assert normalized["symbol"].tolist() == ["10001", "10002", "10001"]
    assert normalized["asset_id"].tolist() == ["10001", "10002", "10001"]


def test_loader_rejects_missing_required_columns() -> None:
    raw = _raw_frame().drop(columns=["Mom12m"])

    with pytest.raises(OAPLoaderError, match="Missing required OAP / JKP columns"):
        normalize_oap_factor_frame(raw, _contract())


def test_loader_rejects_unparseable_dates() -> None:
    raw = _raw_frame()
    raw.loc[0, "date"] = "bad-date-value"

    with pytest.raises(OAPLoaderError, match="Could not parse datetime"):
        normalize_oap_factor_frame(raw, _contract())


def test_loader_rejects_missing_factor_value_by_contract_default() -> None:
    raw = _raw_frame()
    raw.loc[0, "Mom12m"] = None

    with pytest.raises(OAPLoaderError, match="factor_value is required"):
        normalize_oap_factor_frame(raw, _contract())


def test_loader_allows_missing_factor_value_when_contract_allows_it() -> None:
    contract = _contract()
    permissive = replace(contract, validation={**contract.validation, "allow_missing_factor_value": True})
    raw = _raw_frame()
    raw.loc[0, "Mom12m"] = None

    normalized = normalize_oap_factor_frame(raw, permissive)

    assert normalized["factor_value"].isna().sum() == 1


def test_loader_rejects_duplicate_datetime_symbol_when_contract_requires_unique_rows() -> None:
    raw = pd.DataFrame(
        {
            "date": ["2024-01-31", "2024-01-31"],
            "permno": ["10001", "10001"],
            "symbol": ["AAA", "AAA"],
            "Mom12m": [0.1, 0.2],
        }
    )

    with pytest.raises(OAPLoaderError, match="duplicate datetime-symbol"):
        normalize_oap_factor_frame(raw, _contract())


def test_loader_uses_first_day_of_next_month_across_year_boundary() -> None:
    raw = pd.DataFrame(
        {
            "date": ["2024-12-31"],
            "permno": ["10001"],
            "symbol": ["AAA"],
            "Mom12m": [0.1],
        }
    )

    normalized = normalize_oap_factor_frame(raw, _contract())

    assert normalized.loc[0, "datetime"] == pd.Timestamp("2024-12-31")
    assert normalized.loc[0, "available_at"] == pd.Timestamp("2025-01-01")
