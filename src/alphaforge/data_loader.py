from __future__ import annotations

"""Canonical market-data acceptance for AlphaForge.

This module owns the accepted runtime market-data schema, normalization rules,
and post-load validation. Source adapters may pre-shape candidate frames, but
this module decides what counts as accepted market data.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from .config import CSV_COLUMN_ALIASES, MISSING_DATA_POLICY, REQUIRED_COLUMNS
from .schemas import DataSpec

MARKET_DATA_PRICE_COLUMNS = ("open", "high", "low", "close")


def load_market_data(data_spec: DataSpec) -> pd.DataFrame:
    """Load, normalize, and validate the canonical OHLCV runtime frame."""
    frame = pd.read_csv(data_spec.path)
    source_row_count = len(frame)
    frame = _standardize_columns(frame, data_spec.datetime_column)
    frame["datetime"] = pd.to_datetime(frame["datetime"], utc=False, errors="raise")
    frame = frame.sort_values("datetime", kind="mergesort").drop_duplicates(subset=["datetime"], keep="last").reset_index(drop=True)
    deduplicated_row_count = len(frame)
    frame, volume_missing_row_count = _apply_missing_data_policy(frame)
    _validate_market_data(frame, data_spec.path)
    frame.attrs["missing_data_policy"] = MISSING_DATA_POLICY
    frame.attrs["data_quality_summary"] = _build_data_quality_summary(
        source_row_count=source_row_count,
        deduplicated_row_count=deduplicated_row_count,
        accepted_row_count=len(frame),
        volume_missing_row_count=volume_missing_row_count,
    )
    return frame


def split_holdout_data(
    market_data: pd.DataFrame,
    holdout_cutoff_date: str | pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split canonical market data into development and holdout partitions."""
    if "datetime" not in market_data.columns:
        raise ValueError("holdout split requires a datetime column")

    cutoff = _coerce_holdout_cutoff_date(holdout_cutoff_date)
    datetimes = pd.to_datetime(market_data["datetime"], utc=False, errors="raise")
    development_mask = datetimes < cutoff
    holdout_mask = ~development_mask

    development_data = market_data.loc[development_mask].copy().reset_index(drop=True)
    holdout_data = market_data.loc[holdout_mask].copy().reset_index(drop=True)

    if development_data.empty:
        raise ValueError("holdout_cutoff_date removes all development rows")
    if holdout_data.empty:
        raise ValueError("holdout_cutoff_date removes all holdout rows")

    holdout_cutoff_value = cutoff.isoformat()
    for partition in (development_data, holdout_data):
        partition.attrs.update(market_data.attrs)
        partition.attrs["holdout_cutoff_date"] = holdout_cutoff_value
        partition.attrs["development_rows"] = len(development_data)
        partition.attrs["holdout_rows"] = len(holdout_data)
    return development_data, holdout_data


def _standardize_columns(frame: pd.DataFrame, datetime_column: str) -> pd.DataFrame:
    renamed = frame.rename(columns={name: name.strip().lower() for name in frame.columns})
    declared_datetime = datetime_column.strip().lower()
    if declared_datetime in renamed.columns and declared_datetime != "datetime":
        renamed = renamed.rename(columns={declared_datetime: "datetime"})
    renamed = renamed.rename(columns=CSV_COLUMN_ALIASES)
    missing = [column for column in REQUIRED_COLUMNS if column not in renamed.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return renamed[list(REQUIRED_COLUMNS)].copy()


def _apply_missing_data_policy(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    cleaned = frame.copy()
    missing_price_mask = cleaned[list(MARKET_DATA_PRICE_COLUMNS)].isna().any(axis=1)
    if bool(missing_price_mask.any()):
        raise ValueError("Missing OHLC values are not allowed")

    volume_missing_row_count = int(cleaned["volume"].isna().sum())
    cleaned["volume"] = cleaned["volume"].fillna(0.0)
    cleaned[list(MARKET_DATA_PRICE_COLUMNS)] = cleaned[list(MARKET_DATA_PRICE_COLUMNS)].apply(pd.to_numeric, errors="raise")
    cleaned["volume"] = pd.to_numeric(cleaned["volume"], errors="raise")
    return cleaned, volume_missing_row_count


def _validate_market_data(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty:
        raise ValueError(f"No usable rows after cleaning: {path}")
    if frame["datetime"].isna().any():
        raise ValueError("datetime column contains missing values")
    if not frame["datetime"].is_monotonic_increasing:
        raise ValueError("datetime column must be strictly increasing after normalization")
    if frame["datetime"].duplicated().any():
        raise ValueError("datetime column contains duplicates after normalization")

    if not np.isfinite(frame[list(MARKET_DATA_PRICE_COLUMNS)].to_numpy(dtype=float)).all():
        raise ValueError("OHLC values must be finite")
    if (frame[list(MARKET_DATA_PRICE_COLUMNS)] <= 0).any().any():
        raise ValueError("OHLC values must be positive")
    if (frame["high"] < frame["low"]).any():
        raise ValueError("high must be greater than or equal to low")
    if (frame["high"] < frame["open"]).any():
        raise ValueError("high must be greater than or equal to open")
    if (frame["high"] < frame["close"]).any():
        raise ValueError("high must be greater than or equal to close")
    if (frame["low"] > frame["open"]).any():
        raise ValueError("low must be less than or equal to open")
    if (frame["low"] > frame["close"]).any():
        raise ValueError("low must be less than or equal to close")

    if not pd.api.types.is_numeric_dtype(frame["volume"]):
        raise ValueError("Column must be numeric: volume")


def _build_data_quality_summary(
    source_row_count: int,
    deduplicated_row_count: int,
    accepted_row_count: int,
    volume_missing_row_count: int,
) -> dict[str, object]:
    return {
        "required_columns": list(REQUIRED_COLUMNS),
        "canonical_column_order": list(REQUIRED_COLUMNS),
        "datetime_policy": "parse_sort_keep_last",
        "duplicate_datetime_policy": "deterministic_keep_last",
        "missing_ohlc_policy": "fail",
        "missing_volume_policy": "fill_zero",
        "missing_data_policy": MISSING_DATA_POLICY,
        "source_row_count": int(source_row_count),
        "duplicate_row_count": int(source_row_count - deduplicated_row_count),
        "accepted_row_count": int(accepted_row_count),
        "volume_missing_row_count": int(volume_missing_row_count),
    }


def _coerce_holdout_cutoff_date(holdout_cutoff_date: str | pd.Timestamp) -> pd.Timestamp:
    try:
        cutoff = pd.Timestamp(holdout_cutoff_date)
    except Exception as exc:  # pragma: no cover - pandas raises a variety of parse errors
        raise ValueError(f"Invalid holdout_cutoff_date: {holdout_cutoff_date!r}") from exc
    if pd.isna(cutoff):
        raise ValueError(f"Invalid holdout_cutoff_date: {holdout_cutoff_date!r}")
    return cutoff
