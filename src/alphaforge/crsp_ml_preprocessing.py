"""CRSP cross-sectional preprocessing helpers.

This module turns the existing CRSP ML monthly dataset into month-by-month
cross-sectional feature variants. The transformations only use contemporaneous
values from the same month, assume the canonical CRSP ML ``date`` / ``asset_id``
schema, and leave the label column untouched.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from .json_utils import json_safe_float, write_json_artifact


DEFAULT_CRSP_ML_FEATURE_COLUMNS = [
    "mom12_1",
    "mom6_1",
    "mom3_1",
    "ret1_0",
    "volatility_12m",
    "turnover",
    "log_market_cap",
    "log_price",
]

_DATE_COLUMN = "date"
_ASSET_ID_COLUMN = "asset_id"
_LABEL_COLUMN = "forward_1m_total_ret"
_SUPPORTED_METHODS = ("rank", "zscore", "winsorized_zscore")


def validate_preprocessing_frame(
    df: pd.DataFrame,
    *,
    feature_cols: list[str],
) -> None:
    """Validate the structural requirements for CRSP preprocessing."""
    if not feature_cols:
        raise ValueError("feature_cols must not be empty")

    _prepare_preprocessing_frame(
        df,
        feature_cols=feature_cols,
        date_col=_DATE_COLUMN,
        asset_col=_ASSET_ID_COLUMN,
        check_duplicates=True,
    )


def cross_sectional_rank_features(
    df: pd.DataFrame,
    *,
    feature_cols: list[str],
    suffix: str = "_xrank",
) -> pd.DataFrame:
    """Add month-by-month percentile-rank feature transforms."""
    frame = _prepare_preprocessing_frame(
        df,
        feature_cols=feature_cols,
        date_col=_DATE_COLUMN,
        asset_col=_ASSET_ID_COLUMN,
        check_duplicates=True,
    )
    return _add_rank_features(frame, feature_cols=feature_cols, date_col=_DATE_COLUMN, suffix=suffix)


def cross_sectional_zscore_features(
    df: pd.DataFrame,
    *,
    feature_cols: list[str],
    suffix: str = "_xz",
    winsorize: bool = False,
    lower_quantile: float = 0.01,
    upper_quantile: float = 0.99,
) -> pd.DataFrame:
    """Add month-by-month z-scored feature transforms."""
    _validate_quantiles(lower_quantile=lower_quantile, upper_quantile=upper_quantile, winsorize=winsorize)

    frame = _prepare_preprocessing_frame(
        df,
        feature_cols=feature_cols,
        date_col=_DATE_COLUMN,
        asset_col=_ASSET_ID_COLUMN,
        check_duplicates=True,
    )
    return _add_zscore_features(
        frame,
        feature_cols=feature_cols,
        date_col=_DATE_COLUMN,
        suffix=suffix,
        winsorize=winsorize,
        lower_quantile=lower_quantile,
        upper_quantile=upper_quantile,
    )


def build_crsp_ml_preprocessed_dataset(
    df: pd.DataFrame,
    *,
    feature_cols: list[str] | None = None,
    method: str = "rank",
    label_col: str = _LABEL_COLUMN,
    keep_original_features: bool = True,
    lower_quantile: float = 0.01,
    upper_quantile: float = 0.99,
) -> tuple[pd.DataFrame, list[str]]:
    """Build a preprocessed CRSP ML dataset and return its transformed feature columns."""
    resolved_feature_cols = list(DEFAULT_CRSP_ML_FEATURE_COLUMNS if feature_cols is None else feature_cols)
    date_col = _DATE_COLUMN
    asset_col = _ASSET_ID_COLUMN
    if label_col not in df.columns:
        raise ValueError(f"Missing required label column: {label_col!r}")
    frame = _prepare_preprocessing_frame(
        df,
        feature_cols=resolved_feature_cols,
        date_col=date_col,
        asset_col=asset_col,
        check_duplicates=True,
    )

    normalized_method = method.lower()
    transformed_suffix = _method_to_suffix(normalized_method)

    if normalized_method == "rank":
        frame = _add_rank_features(
            frame,
            feature_cols=resolved_feature_cols,
            date_col=date_col,
            suffix=transformed_suffix,
        )
    elif normalized_method == "zscore":
        frame = _add_zscore_features(
            frame,
            feature_cols=resolved_feature_cols,
            date_col=date_col,
            suffix=transformed_suffix,
            winsorize=False,
            lower_quantile=lower_quantile,
            upper_quantile=upper_quantile,
        )
    elif normalized_method == "winsorized_zscore":
        _validate_quantiles(
            lower_quantile=lower_quantile,
            upper_quantile=upper_quantile,
            winsorize=True,
        )
        frame = _add_zscore_features(
            frame,
            feature_cols=resolved_feature_cols,
            date_col=date_col,
            suffix=transformed_suffix,
            winsorize=True,
            lower_quantile=lower_quantile,
            upper_quantile=upper_quantile,
        )
    else:
        raise ValueError(
            f"Unsupported preprocessing method: {method}. "
            f"Supported: {', '.join(_SUPPORTED_METHODS)}"
        )

    transformed_feature_cols = [f"{feature_col}{transformed_suffix}" for feature_col in resolved_feature_cols]

    output_frame = frame.copy()
    if not keep_original_features:
        output_frame = output_frame.drop(columns=resolved_feature_cols)

    output_frame = output_frame.sort_values([date_col, asset_col], kind="mergesort").reset_index(drop=True)
    return output_frame, transformed_feature_cols


def build_crsp_ml_preprocessing_qc(
    df: pd.DataFrame,
    *,
    transformed_feature_cols: list[str],
    label_col: str = _LABEL_COLUMN,
    method: str,
) -> dict[str, object]:
    """Build a deterministic QC payload for a preprocessed CRSP ML dataset."""
    required_columns = {_DATE_COLUMN, _ASSET_ID_COLUMN, label_col, *transformed_feature_cols}
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required preprocessed columns: {sorted(missing)}")

    frame = df.copy()
    frame[_DATE_COLUMN] = pd.to_datetime(frame[_DATE_COLUMN], errors="coerce")
    if frame[_DATE_COLUMN].isna().any():
        invalid_values = frame.loc[frame[_DATE_COLUMN].isna(), _DATE_COLUMN].astype(str).head(5).tolist()
        raise ValueError(f"{_DATE_COLUMN} must be parseable as datetime; invalid values: {invalid_values}")
    frame[_DATE_COLUMN] = (frame[_DATE_COLUMN] + pd.offsets.MonthEnd(0)).dt.normalize()

    row_count = int(len(frame))
    return {
        "rows": row_count,
        "assets": int(frame[_ASSET_ID_COLUMN].nunique(dropna=True)),
        "date_min": _iso_date(frame[_DATE_COLUMN].min()) if row_count else None,
        "date_max": _iso_date(frame[_DATE_COLUMN].max()) if row_count else None,
        "months": int(frame[_DATE_COLUMN].dt.to_period("M").nunique()) if row_count else 0,
        "method": method,
        "transformed_feature_columns": list(transformed_feature_cols),
        "label_column": label_col,
        "duplicate_asset_date_rows": int(frame[[_ASSET_ID_COLUMN, _DATE_COLUMN]].duplicated().sum() if row_count else 0),
        "missing_label_ratio": _missing_ratio(frame, label_col),
        **{
            f"missing_{column}_ratio": _missing_ratio(frame, column)
            for column in transformed_feature_cols
        },
        "frequency": "monthly",
    }


def write_feature_columns_json(
    path: str | Path,
    feature_cols: list[str],
    *,
    raw_feature_cols: list[str] | None = None,
    method: str | None = None,
    label_col: str = _LABEL_COLUMN,
    keep_original_features: bool | None = None,
    lower_quantile: float | None = None,
    upper_quantile: float | None = None,
) -> None:
    """Write a JSON artifact describing transformed feature columns and metadata."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_artifact(
        path,
        {
            "feature_columns": list(feature_cols),
            "count": int(len(feature_cols)),
            "raw_feature_columns": list(raw_feature_cols) if raw_feature_cols is not None else None,
            "method": method,
            "label_column": label_col,
            "date_column": _DATE_COLUMN,
            "asset_column": _ASSET_ID_COLUMN,
            "keep_original_features": keep_original_features,
            "lower_quantile": json_safe_float(lower_quantile),
            "upper_quantile": json_safe_float(upper_quantile),
        },
    )


def _prepare_preprocessing_frame(
    df: pd.DataFrame,
    *,
    feature_cols: list[str],
    date_col: str,
    asset_col: str,
    check_duplicates: bool,
) -> pd.DataFrame:
    if not feature_cols:
        raise ValueError("feature_cols must not be empty")

    required_columns = [date_col, asset_col, *feature_cols]
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required preprocessing columns: {sorted(missing)}")

    frame = df.copy()
    frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    if frame[date_col].isna().any():
        invalid_values = frame.loc[frame[date_col].isna(), date_col].astype(str).head(5).tolist()
        raise ValueError(f"{date_col} must be parseable as datetime; invalid values: {invalid_values}")
    frame[date_col] = (frame[date_col] + pd.offsets.MonthEnd(0)).dt.normalize()

    if frame[asset_col].isna().any():
        raise ValueError(f"{asset_col} must be non-null")
    if frame[asset_col].astype("string").str.strip().eq("").any():
        raise ValueError(f"{asset_col} must be non-empty")
    frame[asset_col] = frame[asset_col].astype(str)

    for feature_col in feature_cols:
        frame[feature_col] = pd.to_numeric(frame[feature_col], errors="coerce")

    duplicate_message = (
        "duplicate asset_id/date rows are not allowed"
        if asset_col == _ASSET_ID_COLUMN and date_col == _DATE_COLUMN
        else f"duplicate {asset_col}/{date_col} rows are not allowed"
    )
    if check_duplicates and frame[[asset_col, date_col]].duplicated().any():
        raise ValueError(duplicate_message)

    return frame


def _add_rank_features(
    frame: pd.DataFrame,
    *,
    feature_cols: list[str],
    date_col: str,
    suffix: str,
) -> pd.DataFrame:
    output = frame.copy()
    for feature_col in feature_cols:
        transformed_col = f"{feature_col}{suffix}"
        output[transformed_col] = output.groupby(date_col, sort=False)[feature_col].transform(
            lambda series: series.rank(pct=True, method="average") - 0.5
        )
    return output


def _add_zscore_features(
    frame: pd.DataFrame,
    *,
    feature_cols: list[str],
    date_col: str,
    suffix: str,
    winsorize: bool,
    lower_quantile: float,
    upper_quantile: float,
) -> pd.DataFrame:
    output = frame.copy()
    for feature_col in feature_cols:
        transformed_col = f"{feature_col}{suffix}"
        output[transformed_col] = output.groupby(date_col, sort=False)[feature_col].transform(
            lambda series: _cross_sectional_zscore_series(
                series,
                winsorize=winsorize,
                lower_quantile=lower_quantile,
                upper_quantile=upper_quantile,
            )
        )
    return output


def _cross_sectional_zscore_series(
    series: pd.Series,
    *,
    winsorize: bool,
    lower_quantile: float,
    upper_quantile: float,
) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    result = pd.Series(np.nan, index=series.index, dtype=float)

    valid_mask = values.notna()
    if not valid_mask.any():
        return result

    valid_values = values.loc[valid_mask].astype(float)
    if winsorize:
        lower_bound = float(valid_values.quantile(lower_quantile))
        upper_bound = float(valid_values.quantile(upper_quantile))
        valid_values = valid_values.clip(lower=lower_bound, upper=upper_bound)

    std = float(valid_values.std(ddof=1))
    if not np.isfinite(std) or math.isclose(std, 0.0):
        result.loc[valid_mask] = 0.0
        return result

    mean = float(valid_values.mean())
    result.loc[valid_mask] = (valid_values - mean) / std
    return result


def _validate_quantiles(*, lower_quantile: float, upper_quantile: float, winsorize: bool) -> None:
    if not winsorize:
        return
    if not np.isfinite(lower_quantile) or not np.isfinite(upper_quantile):
        raise ValueError("lower_quantile and upper_quantile must be finite")
    if lower_quantile < 0.0 or lower_quantile > 1.0:
        raise ValueError("lower_quantile must be between 0 and 1")
    if upper_quantile < 0.0 or upper_quantile > 1.0:
        raise ValueError("upper_quantile must be between 0 and 1")
    if lower_quantile > upper_quantile:
        raise ValueError("lower_quantile must be less than or equal to upper_quantile")


def _method_to_suffix(method: str) -> str:
    if method == "rank":
        return "_xrank"
    if method == "zscore":
        return "_xz"
    if method == "winsorized_zscore":
        return "_xwz"
    raise ValueError(
        f"Unsupported preprocessing method: {method}. "
        f"Supported: {', '.join(_SUPPORTED_METHODS)}"
    )


def _missing_ratio(df: pd.DataFrame, column: str) -> float:
    if df.empty:
        return 0.0
    return json_safe_float(df[column].isna().mean()) or 0.0


def _iso_date(value: object) -> str | None:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()
