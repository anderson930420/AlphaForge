from __future__ import annotations

"""Canonical market-data acceptance for AlphaForge.

This module owns the accepted runtime market-data schema, normalization rules,
and post-load validation. Source adapters may pre-shape candidate frames, but
this module decides what counts as accepted market data.
"""

from pathlib import Path

import pandas as pd

from .config import CSV_COLUMN_ALIASES, MISSING_DATA_POLICY, REQUIRED_COLUMNS
from .schemas import DataSpec

MARKET_DATA_PRICE_COLUMNS = ("open", "high", "low", "close")


def load_market_data(data_spec: DataSpec) -> pd.DataFrame:
    """Load, normalize, and validate the canonical OHLCV runtime frame."""
    frame = pd.read_csv(data_spec.path)
    frame = _standardize_columns(frame, data_spec.datetime_column)
    frame["datetime"] = pd.to_datetime(frame["datetime"], utc=False, errors="coerce")
    frame = frame.sort_values("datetime").drop_duplicates(subset=["datetime"], keep="last")
    frame = _apply_missing_data_policy(frame)
    _validate_market_data(frame, data_spec.path)
    return frame.reset_index(drop=True)


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


def _apply_missing_data_policy(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.dropna(subset=["datetime", "close"]).copy()
    cleaned[list(MARKET_DATA_PRICE_COLUMNS)] = cleaned[list(MARKET_DATA_PRICE_COLUMNS)].ffill()
    cleaned["volume"] = cleaned["volume"].fillna(0.0)
    cleaned = cleaned.dropna(subset=list(MARKET_DATA_PRICE_COLUMNS))
    cleaned.attrs["missing_data_policy"] = MISSING_DATA_POLICY
    return cleaned


def _validate_market_data(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty:
        raise ValueError(f"No usable rows after cleaning: {path}")
    if not frame["datetime"].is_monotonic_increasing:
        raise ValueError("datetime column must be sorted ascending after cleaning")
    if frame["datetime"].duplicated().any():
        raise ValueError("datetime column contains duplicates after cleaning")
    for column in ["open", "high", "low", "close", "volume"]:
        if not pd.api.types.is_numeric_dtype(frame[column]):
            raise ValueError(f"Column must be numeric: {column}")


def _coerce_holdout_cutoff_date(holdout_cutoff_date: str | pd.Timestamp) -> pd.Timestamp:
    try:
        cutoff = pd.Timestamp(holdout_cutoff_date)
    except Exception as exc:  # pragma: no cover - pandas raises a variety of parse errors
        raise ValueError(f"Invalid holdout_cutoff_date: {holdout_cutoff_date!r}") from exc
    if pd.isna(cutoff):
        raise ValueError(f"Invalid holdout_cutoff_date: {holdout_cutoff_date!r}")
    return cutoff
