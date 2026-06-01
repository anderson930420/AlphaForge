"""Canonical loader and QC helpers for external CRSP monthly panels.

This module only reads and validates an externally generated monthly parquet
panel. It does not copy raw CRSP data, build factors, or change backtest or ML
behavior.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


CRSP_MONTHLY_PANEL_COLUMNS = [
    "date",
    "asset_id",
    "permno",
    "permco",
    "ticker",
    "cusip",
    "ncusip",
    "exchcd",
    "shrcd",
    "siccd",
    "price",
    "ret",
    "retx",
    "dlret",
    "volume",
    "shares_out",
    "market_cap",
    "lag_market_cap",
    "total_ret",
    "is_common_share",
    "is_primary_us_exchange",
    "daily_obs_count",
    "first_trading_date",
    "last_trading_date",
]


_CRSP_QC_COLUMNS = [
    "date",
    "asset_id",
    "ret",
    "total_ret",
    "price",
    "market_cap",
    "lag_market_cap",
    "is_common_share",
    "is_primary_us_exchange",
]

_BOOLEAN_COLUMN_MAP = {
    "true": True,
    "false": False,
    "1": True,
    "0": False,
    "t": True,
    "f": False,
    "yes": True,
    "no": False,
    "y": True,
    "n": False,
}


def validate_crsp_monthly_panel(df: pd.DataFrame) -> None:
    """Validate the canonical CRSP monthly panel contract."""
    _require_columns(df, CRSP_MONTHLY_PANEL_COLUMNS)

    date_values = _coerce_datetime_series(df["date"], "date")
    if df["asset_id"].isna().any():
        raise ValueError("asset_id must be non-null")
    if df["asset_id"].astype("string").str.strip().eq("").any():
        raise ValueError("asset_id must be non-null")

    _coerce_boolean_like_series(df["is_common_share"], "is_common_share")
    _coerce_boolean_like_series(df["is_primary_us_exchange"], "is_primary_us_exchange")

    duplicate_rows = pd.DataFrame({"asset_id": df["asset_id"], "date": date_values}).duplicated()
    if duplicate_rows.any():
        raise ValueError("duplicate asset_id/date rows are not allowed")


def load_crsp_monthly_panel(
    path: str | Path,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    common_shares_only: bool = False,
    primary_exchange_only: bool = False,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Load an external CRSP monthly parquet panel and apply optional filters."""
    frame = pd.read_parquet(Path(path))
    frame = _normalize_crsp_monthly_panel_frame(frame)

    if start_date is not None:
        start = _parse_filter_date(start_date, "start_date")
        frame = frame.loc[frame["date"] >= start]
    if end_date is not None:
        end = _parse_filter_date(end_date, "end_date")
        frame = frame.loc[frame["date"] <= end]
    if common_shares_only:
        frame = frame.loc[frame["is_common_share"]]
    if primary_exchange_only:
        frame = frame.loc[frame["is_primary_us_exchange"]]

    frame = frame.sort_values(["asset_id", "date"], kind="mergesort").reset_index(drop=True)
    validate_crsp_monthly_panel(frame)

    if columns is None:
        return frame.reindex(columns=CRSP_MONTHLY_PANEL_COLUMNS).reset_index(drop=True)

    missing_requested = [column for column in columns if column not in frame.columns]
    if missing_requested:
        raise ValueError(f"Requested columns are missing from CRSP monthly panel: {missing_requested}")
    return frame.loc[:, columns].reset_index(drop=True)


def build_crsp_monthly_panel_qc(df: pd.DataFrame) -> dict:
    """Build a small QC payload for an external CRSP monthly panel."""
    _require_columns(df, _CRSP_QC_COLUMNS)

    date_values = _coerce_datetime_series(df["date"], "date")
    common_share_values = _coerce_boolean_like_series(df["is_common_share"], "is_common_share")
    primary_exchange_values = _coerce_boolean_like_series(
        df["is_primary_us_exchange"],
        "is_primary_us_exchange",
    )

    row_count = int(len(df))

    def missing_ratio(column: str) -> float:
        if row_count == 0:
            return 0.0
        return float(df[column].isna().mean())

    return {
        "rows": row_count,
        "assets": int(df["asset_id"].nunique(dropna=True)),
        "date_min": _datetime_to_date_string(date_values.min()) if row_count else None,
        "date_max": _datetime_to_date_string(date_values.max()) if row_count else None,
        "months": int(date_values.dt.to_period("M").nunique()) if row_count else 0,
        "duplicate_asset_date_rows": int(
            pd.DataFrame({"asset_id": df["asset_id"], "date": date_values}).duplicated().sum()
        ),
        "missing_ret_ratio": missing_ratio("ret"),
        "missing_total_ret_ratio": missing_ratio("total_ret"),
        "missing_price_ratio": missing_ratio("price"),
        "missing_market_cap_ratio": missing_ratio("market_cap"),
        "missing_lag_market_cap_ratio": missing_ratio("lag_market_cap"),
        "common_share_rows": int(common_share_values.sum()),
        "primary_exchange_rows": int(primary_exchange_values.sum()),
        "frequency": "monthly",
    }


def _normalize_crsp_monthly_panel_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized["date"] = _coerce_datetime_series(normalized["date"], "date")
    normalized["is_common_share"] = _coerce_boolean_like_series(
        normalized["is_common_share"],
        "is_common_share",
    )
    normalized["is_primary_us_exchange"] = _coerce_boolean_like_series(
        normalized["is_primary_us_exchange"],
        "is_primary_us_exchange",
    )
    return normalized


def _require_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required CRSP monthly panel columns: {missing}")


def _coerce_datetime_series(series: pd.Series, field_name: str) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.isna().any():
        invalid_values = series[parsed.isna()].astype(str).head(5).tolist()
        raise ValueError(f"{field_name} must be parseable as datetime; invalid values: {invalid_values}")
    return parsed


def _coerce_boolean_like_series(series: pd.Series, field_name: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        if series.isna().any():
            raise ValueError(f"{field_name} must be boolean-like; invalid values: ['<NA>']")
        return series.astype(bool)

    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().all() and set(numeric.dropna().unique()).issubset({0, 1}):
        return numeric.astype(int).astype(bool)

    normalized = series.astype("string").str.strip().str.lower()
    mapped = normalized.map(_BOOLEAN_COLUMN_MAP)
    if mapped.isna().any():
        invalid_values = series[mapped.isna()].astype(str).head(5).tolist()
        raise ValueError(f"{field_name} must be boolean-like; invalid values: {invalid_values}")
    return mapped.astype(bool)


def _parse_filter_date(value: str, field_name: str) -> pd.Timestamp:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"{field_name} must be parseable as datetime: {value!r}")
    return pd.Timestamp(parsed)


def _datetime_to_date_string(value: pd.Timestamp) -> str:
    return pd.Timestamp(value).date().isoformat()
