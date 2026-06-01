"""CRSP monthly supervised-learning dataset helpers.

This module turns the external canonical CRSP monthly panel into an
ML-ready monthly asset panel with deterministic trailing features and a
next-month return label. It does not train models or change backtest behavior.
"""

from __future__ import annotations

from numpy.lib.stride_tricks import sliding_window_view

import numpy as np
import pandas as pd

from .json_utils import json_safe_float


CRSP_ML_CONTEXT_COLUMNS = [
    "date",
    "asset_id",
    "permno",
    "ticker",
    "price",
    "market_cap",
    "lag_market_cap",
    "total_ret",
]

CRSP_ML_FEATURE_COLUMNS = [
    "mom12_1",
    "mom6_1",
    "mom3_1",
    "ret1_0",
    "volatility_12m",
    "turnover",
    "log_market_cap",
    "log_price",
]

CRSP_ML_LABEL_COLUMN = "forward_1m_total_ret"

_REQUIRED_INPUT_COLUMNS = [
    "date",
    "asset_id",
    "permno",
    "ticker",
    "total_ret",
    "ret",
    "retx",
    "dlret",
    "price",
    "volume",
    "shares_out",
    "market_cap",
    "lag_market_cap",
]


def build_crsp_ml_features(
    panel: pd.DataFrame,
    *,
    min_mom_obs: int = 8,
) -> pd.DataFrame:
    """Build deterministic trailing CRSP features from a canonical monthly panel."""
    _validate_feature_input(panel, min_mom_obs=min_mom_obs)

    if panel.empty:
        return _empty_feature_frame()

    frame = _normalize_panel(panel)
    frame = frame.sort_values(["asset_id", "date"], kind="mergesort").reset_index(drop=True)
    _validate_unique_asset_date(frame)

    feature_frames: list[pd.DataFrame] = []
    for _, asset_frame in frame.groupby("asset_id", sort=False):
        feature_frames.append(_build_asset_feature_frame(asset_frame, min_mom_obs=min_mom_obs))

    if not feature_frames:
        return _empty_feature_frame()

    return pd.concat(feature_frames, ignore_index=True)


def add_forward_return_label(
    features: pd.DataFrame,
    *,
    return_col: str = "total_ret",
    label_col: str = CRSP_ML_LABEL_COLUMN,
) -> pd.DataFrame:
    """Add a next-month forward return label by asset."""
    required_columns = {"date", "asset_id", return_col}
    missing = required_columns - set(features.columns)
    if missing:
        raise ValueError(f"Missing required feature columns: {sorted(missing)}")

    if features.empty:
        frame = features.copy()
        frame[label_col] = pd.Series(dtype=float)
        return frame.reindex(columns=[*features.columns, label_col])

    frame = features.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if frame["date"].isna().any():
        invalid_values = frame.loc[frame["date"].isna(), "date"].astype(str).head(5).tolist()
        raise ValueError(f"date must be parseable as datetime; invalid values: {invalid_values}")

    frame["asset_id"] = frame["asset_id"].astype(str)
    frame = frame.sort_values(["asset_id", "date"], kind="mergesort").reset_index(drop=True)
    frame[return_col] = pd.to_numeric(frame[return_col], errors="coerce")
    frame[label_col] = frame.groupby("asset_id", sort=False)[return_col].shift(-1)
    return frame


def build_crsp_ml_dataset(
    panel: pd.DataFrame,
    *,
    min_mom_obs: int = 8,
    drop_missing_label: bool = True,
    drop_missing_features: bool = False,
) -> pd.DataFrame:
    """Build an ML-ready CRSP monthly dataset with trailing features and label."""
    features = build_crsp_ml_features(panel, min_mom_obs=min_mom_obs)
    dataset = add_forward_return_label(features)

    if drop_missing_label:
        dataset = dataset.dropna(subset=[CRSP_ML_LABEL_COLUMN])
    if drop_missing_features:
        dataset = dataset.dropna(subset=CRSP_ML_FEATURE_COLUMNS)

    if dataset.empty:
        return _empty_dataset_frame()

    dataset = dataset.sort_values(["date", "asset_id"], kind="mergesort").reset_index(drop=True)
    return dataset.loc[:, [*CRSP_ML_CONTEXT_COLUMNS, *CRSP_ML_FEATURE_COLUMNS, CRSP_ML_LABEL_COLUMN]]


def build_crsp_ml_dataset_qc(df: pd.DataFrame) -> dict[str, object]:
    """Build a QC payload for an ML-ready CRSP monthly dataset."""
    required_columns = {"date", "asset_id", CRSP_ML_LABEL_COLUMN, *CRSP_ML_FEATURE_COLUMNS}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing required dataset columns: {sorted(missing)}")

    frame = df.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if frame["date"].isna().any():
        invalid_values = frame.loc[frame["date"].isna(), "date"].astype(str).head(5).tolist()
        raise ValueError(f"date must be parseable as datetime; invalid values: {invalid_values}")

    row_count = int(len(frame))
    return {
        "rows": row_count,
        "assets": int(frame["asset_id"].nunique(dropna=True)),
        "date_min": _iso_date(frame["date"].min()) if row_count else None,
        "date_max": _iso_date(frame["date"].max()) if row_count else None,
        "months": int(frame["date"].dt.to_period("M").nunique()) if row_count else 0,
        "feature_columns": list(CRSP_ML_FEATURE_COLUMNS),
        "label_column": CRSP_ML_LABEL_COLUMN,
        "missing_label_ratio": _missing_ratio(frame, CRSP_ML_LABEL_COLUMN),
        "missing_mom12_1_ratio": _missing_ratio(frame, "mom12_1"),
        "missing_mom6_1_ratio": _missing_ratio(frame, "mom6_1"),
        "missing_mom3_1_ratio": _missing_ratio(frame, "mom3_1"),
        "missing_ret1_0_ratio": _missing_ratio(frame, "ret1_0"),
        "missing_volatility_12m_ratio": _missing_ratio(frame, "volatility_12m"),
        "missing_turnover_ratio": _missing_ratio(frame, "turnover"),
        "missing_log_market_cap_ratio": _missing_ratio(frame, "log_market_cap"),
        "missing_log_price_ratio": _missing_ratio(frame, "log_price"),
        "duplicate_asset_date_rows": int(
            frame[["asset_id", "date"]].duplicated().sum() if row_count else 0
        ),
        "frequency": "monthly",
    }


def _build_asset_feature_frame(asset_frame: pd.DataFrame, *, min_mom_obs: int) -> pd.DataFrame:
    frame = asset_frame.copy()
    total_ret = pd.to_numeric(frame["total_ret"], errors="coerce").to_numpy(dtype=float, copy=True)
    price = pd.to_numeric(frame["price"], errors="coerce").to_numpy(dtype=float, copy=True)
    volume = pd.to_numeric(frame["volume"], errors="coerce").to_numpy(dtype=float, copy=True)
    shares_out = pd.to_numeric(frame["shares_out"], errors="coerce").to_numpy(dtype=float, copy=True)
    lag_market_cap = pd.to_numeric(frame["lag_market_cap"], errors="coerce").to_numpy(dtype=float, copy=True)

    frame["mom12_1"] = _compute_shifted_cumulative_return(total_ret, window_size=11, min_obs=min_mom_obs)
    frame["mom6_1"] = _compute_shifted_cumulative_return(total_ret, window_size=5, min_obs=5)
    frame["mom3_1"] = _compute_shifted_cumulative_return(total_ret, window_size=2, min_obs=2)
    frame["ret1_0"] = total_ret
    frame["volatility_12m"] = _compute_trailing_volatility(total_ret, window_size=12)
    frame["turnover"] = _safe_ratio(volume, shares_out)
    frame["log_market_cap"] = _safe_log(lag_market_cap)
    frame["log_price"] = _safe_log(price)

    output_columns = [
        *CRSP_ML_CONTEXT_COLUMNS,
        *CRSP_ML_FEATURE_COLUMNS,
    ]
    return frame.loc[:, output_columns].reset_index(drop=True)


def _compute_shifted_cumulative_return(
    values: np.ndarray,
    *,
    window_size: int,
    min_obs: int,
    skip_recent: int = 2,
) -> np.ndarray:
    if len(values) == 0:
        return np.empty(0, dtype=float)
    if window_size < 1:
        raise ValueError("window_size must be >= 1")
    if min_obs < 1:
        raise ValueError("min_obs must be >= 1")
    if skip_recent < 0:
        raise ValueError("skip_recent must be >= 0")

    lookback = np.full(len(values), np.nan, dtype=float)
    if len(values) > skip_recent:
        lookback[skip_recent:] = values[:-skip_recent]

    padded = np.concatenate([np.full(window_size - 1, np.nan, dtype=float), lookback])
    windows = sliding_window_view(padded, window_size)
    valid = np.isfinite(windows)
    counts = valid.sum(axis=1)
    factors = np.where(valid, 1.0 + windows, 1.0)
    cumulative = np.prod(factors, axis=1) - 1.0
    cumulative[counts < min_obs] = np.nan
    return cumulative.astype(float, copy=False)


def _compute_trailing_volatility(values: np.ndarray, *, window_size: int) -> np.ndarray:
    if len(values) == 0:
        return np.empty(0, dtype=float)
    series = pd.Series(values, dtype=float)
    return series.rolling(window=window_size, min_periods=window_size).std(ddof=1).to_numpy(dtype=float)


def _safe_ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    result = np.full(len(numerator), np.nan, dtype=float)
    valid = np.isfinite(numerator) & np.isfinite(denominator) & (denominator > 0)
    result[valid] = numerator[valid] / denominator[valid]
    return result


def _safe_log(values: np.ndarray) -> np.ndarray:
    result = np.full(len(values), np.nan, dtype=float)
    valid = np.isfinite(values) & (values > 0)
    result[valid] = np.log(values[valid])
    return result


def _normalize_panel(panel: pd.DataFrame) -> pd.DataFrame:
    frame = panel.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if frame["date"].isna().any():
        invalid_values = frame.loc[frame["date"].isna(), "date"].astype(str).head(5).tolist()
        raise ValueError(f"date must be parseable as datetime; invalid values: {invalid_values}")
    frame["date"] = frame["date"] + pd.offsets.MonthEnd(0)
    if frame["asset_id"].isna().any():
        raise ValueError("asset_id must be non-null")
    frame["asset_id"] = frame["asset_id"].astype(str)

    numeric_columns = [
        "total_ret",
        "ret",
        "retx",
        "dlret",
        "price",
        "volume",
        "shares_out",
        "market_cap",
        "lag_market_cap",
    ]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _validate_feature_input(panel: pd.DataFrame, *, min_mom_obs: int) -> None:
    if min_mom_obs < 1:
        raise ValueError("min_mom_obs must be >= 1")
    missing = [column for column in _REQUIRED_INPUT_COLUMNS if column not in panel.columns]
    if missing:
        raise ValueError(f"Missing required CRSP ML input columns: {missing}")


def _validate_unique_asset_date(frame: pd.DataFrame) -> None:
    duplicates = frame[["asset_id", "date"]].duplicated()
    if duplicates.any():
        raise ValueError("duplicate asset_id/date rows are not allowed")


def _missing_ratio(df: pd.DataFrame, column: str) -> float:
    if df.empty:
        return 0.0
    return json_safe_float(df[column].isna().mean()) or 0.0


def _iso_date(value: object) -> str | None:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()


def _empty_feature_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=[*CRSP_ML_CONTEXT_COLUMNS, *CRSP_ML_FEATURE_COLUMNS])


def _empty_dataset_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=[*CRSP_ML_CONTEXT_COLUMNS, *CRSP_ML_FEATURE_COLUMNS, CRSP_ML_LABEL_COLUMN])
