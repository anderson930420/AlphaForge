from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import CSV_COLUMN_ALIASES, MISSING_DATA_POLICY, REQUIRED_COLUMNS
from .schemas import DataSpec


def load_market_data(data_spec: DataSpec) -> pd.DataFrame:
    """Load and standardize OHLCV data from CSV."""
    frame = pd.read_csv(data_spec.path)
    frame = _standardize_columns(frame)
    frame["datetime"] = pd.to_datetime(frame["datetime"], utc=False, errors="coerce")
    frame = frame.sort_values("datetime").drop_duplicates(subset=["datetime"], keep="last")
    frame = _apply_missing_data_policy(frame)
    _validate_market_data(frame, data_spec.path)
    return frame.reset_index(drop=True)


def _standardize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.rename(columns={name: name.strip().lower() for name in frame.columns})
    renamed = renamed.rename(columns=CSV_COLUMN_ALIASES)
    missing = [column for column in REQUIRED_COLUMNS if column not in renamed.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return renamed[REQUIRED_COLUMNS].copy()


def _apply_missing_data_policy(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.dropna(subset=["datetime", "close"]).copy()
    price_columns = ["open", "high", "low", "close"]
    cleaned[price_columns] = cleaned[price_columns].ffill()
    cleaned["volume"] = cleaned["volume"].fillna(0.0)
    cleaned = cleaned.dropna(subset=price_columns)
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
