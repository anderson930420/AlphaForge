from __future__ import annotations

"""Canonical market-data acceptance for AlphaForge.

This module owns the accepted runtime market-data schema, normalization rules,
and post-load validation. Source adapters may pre-shape candidate frames, but
this module decides what counts as accepted market data.
"""

from pathlib import Path

import pandas as pd

from .schemas import DataSpec

MARKET_DATA_REQUIRED_COLUMNS = ("datetime", "open", "high", "low", "close", "volume")
MARKET_DATA_PRICE_COLUMNS = ("open", "high", "low", "close")
MARKET_DATA_COLUMN_ALIASES = {
    "date": "datetime",
    "timestamp": "datetime",
}
MARKET_DATA_MISSING_DATA_POLICY = (
    "Drop rows with missing datetime or close values, forward-fill open/high/low/close,"
    " and fill missing volume with 0 after sorting."
)


def load_market_data(data_spec: DataSpec) -> pd.DataFrame:
    """Load and standardize OHLCV data from CSV."""
    frame = pd.read_csv(data_spec.path)
    frame = _standardize_columns(frame, data_spec.datetime_column)
    frame["datetime"] = pd.to_datetime(frame["datetime"], utc=False, errors="coerce")
    frame = frame.sort_values("datetime").drop_duplicates(subset=["datetime"], keep="last")
    frame = _apply_missing_data_policy(frame)
    _validate_market_data(frame, data_spec.path)
    return frame.reset_index(drop=True)


def _standardize_columns(frame: pd.DataFrame, datetime_column: str) -> pd.DataFrame:
    renamed = frame.rename(columns={name: name.strip().lower() for name in frame.columns})
    declared_datetime = datetime_column.strip().lower()
    if declared_datetime in renamed.columns and declared_datetime != "datetime":
        renamed = renamed.rename(columns={declared_datetime: "datetime"})
    renamed = renamed.rename(columns=MARKET_DATA_COLUMN_ALIASES)
    missing = [column for column in MARKET_DATA_REQUIRED_COLUMNS if column not in renamed.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return renamed[list(MARKET_DATA_REQUIRED_COLUMNS)].copy()


def _apply_missing_data_policy(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.dropna(subset=["datetime", "close"]).copy()
    cleaned[list(MARKET_DATA_PRICE_COLUMNS)] = cleaned[list(MARKET_DATA_PRICE_COLUMNS)].ffill()
    cleaned["volume"] = cleaned["volume"].fillna(0.0)
    cleaned = cleaned.dropna(subset=list(MARKET_DATA_PRICE_COLUMNS))
    cleaned.attrs["missing_data_policy"] = MARKET_DATA_MISSING_DATA_POLICY
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
