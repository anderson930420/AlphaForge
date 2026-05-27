"""OAP / JKP factor file loading utilities.

Phase 13 reads local OAP / JKP-style factor files and normalizes them according
to the Phase 12 factor contract. It does not download remote datasets, run
backtests, or change AlphaForge's signal schema.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from alphaforge.oap_factor_contract import OAPFactorContract


OAP_FACTOR_FRAME_COLUMNS = (
    "datetime",
    "available_at",
    "symbol",
    "asset_id",
    "factor_name",
    "factor_value",
    "source",
)


class OAPLoaderError(ValueError):
    """Raised when an OAP / JKP factor file cannot be normalized."""


def load_oap_factor_frame(path: str | Path, contract: OAPFactorContract) -> pd.DataFrame:
    """Load a local OAP / JKP CSV and return a normalized factor frame.

    The normalized frame is intentionally upstream of signal generation. It does
    not produce `direction` or `target_weight`; later adapter phases should map
    `factor_value` through the contract's `decision_rule`.
    """
    raw = pd.read_csv(Path(path))
    return normalize_oap_factor_frame(raw, contract)


def normalize_oap_factor_frame(raw_frame: pd.DataFrame, contract: OAPFactorContract) -> pd.DataFrame:
    """Normalize an already-loaded OAP / JKP-like DataFrame.

    Output columns:
    - datetime: rebalance date materialized from the contract timing policy
    - available_at: date when the raw characteristic was observable
    - symbol: string symbol used by downstream AlphaForge signal files
    - asset_id: stable upstream asset identifier
    - factor_name: contract factor name
    - factor_value: numeric characteristic value
    - source: dataset/provider release label
    """
    _validate_required_raw_columns(raw_frame, contract)

    timing = contract.timing
    factor = contract.factor
    identity = contract.identity
    validation = contract.validation

    raw_datetime = _normalize_daily_dates(raw_frame[timing["datetime_col"]], "datetime")
    available_at = _materialize_available_at(raw_datetime, str(timing["available_at_policy"]))

    asset_id = raw_frame[identity["asset_id_col"]].astype(str)
    symbol_col = identity["symbol_col"]
    symbol = raw_frame[symbol_col].astype(str) if symbol_col in raw_frame.columns else asset_id.copy()

    factor_value = pd.to_numeric(raw_frame[factor["raw_column"]], errors="coerce")

    output = pd.DataFrame(
        {
            "datetime": raw_datetime,
            "available_at": available_at,
            "symbol": symbol,
            "asset_id": asset_id,
            "factor_name": str(factor["name"]),
            "factor_value": factor_value,
            "source": _build_source_label(contract),
        }
    )

    _validate_normalized_oap_factor_frame(output, validation)
    return output.reindex(columns=OAP_FACTOR_FRAME_COLUMNS).sort_values(["datetime", "symbol"]).reset_index(drop=True)


def _validate_required_raw_columns(raw_frame: pd.DataFrame, contract: OAPFactorContract) -> None:
    required = [
        contract.timing["datetime_col"],
        contract.identity["asset_id_col"],
        contract.factor["raw_column"],
    ]
    missing = [column for column in required if column not in raw_frame.columns]
    if missing:
        raise OAPLoaderError(f"Missing required OAP / JKP columns: {missing}")


def _materialize_available_at(raw_datetime: pd.Series, policy: str) -> pd.Series:
    if policy != "next_month":
        raise OAPLoaderError(f"Unsupported available_at policy for OAP loader: {policy!r}")
    return raw_datetime.map(_first_day_of_next_month)


def _first_day_of_next_month(value: pd.Timestamp) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    month_start = pd.Timestamp(year=value.year, month=value.month, day=1)
    return month_start + pd.offsets.MonthBegin(1)


def _normalize_daily_dates(values: pd.Series, field_name: str) -> pd.Series:
    def normalize(value: object) -> pd.Timestamp:
        if pd.isna(value):
            return pd.NaT
        try:
            parsed = pd.to_datetime(value, errors="raise")
        except (TypeError, ValueError) as exc:
            raise OAPLoaderError(f"Could not parse {field_name} value {value!r}") from exc
        return pd.Timestamp(parsed.date())

    return values.map(normalize)


def _build_source_label(contract: OAPFactorContract) -> str:
    dataset = contract.dataset
    parts = [str(dataset["name"]), str(dataset["provider"]), str(dataset["release"])]
    return ":".join(part for part in parts if part and part != "unknown")


def _validate_normalized_oap_factor_frame(frame: pd.DataFrame, validation: dict[str, Any]) -> None:
    if frame["datetime"].isna().any():
        raise OAPLoaderError("datetime is required")
    if frame["available_at"].isna().any():
        raise OAPLoaderError("available_at is required")
    if frame["symbol"].isna().any() or frame["symbol"].astype(str).eq("").any():
        raise OAPLoaderError("symbol is required")
    if frame["asset_id"].isna().any() or frame["asset_id"].astype(str).eq("").any():
        raise OAPLoaderError("asset_id is required")
    if bool(validation.get("allow_missing_factor_value", False)) is False and frame["factor_value"].isna().any():
        raise OAPLoaderError("factor_value is required")
    if bool(validation.get("require_unique_datetime_symbol", False)) and frame.duplicated(
        subset=["datetime", "symbol"]
    ).any():
        raise OAPLoaderError("duplicate datetime-symbol factor rows are not allowed")
    if (frame["available_at"] < frame["datetime"]).any():
        raise OAPLoaderError("available_at must be greater than or equal to datetime for next_month policy")
