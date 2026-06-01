"""Deterministic walk-forward split helpers for CRSP ML datasets.

This module only slices an existing CRSP ML dataset into month-end aware
train/test windows and emits QC metadata. It does not train models, alter
feature construction, or change backtest behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


_ASSET_ID_COLUMN = "asset_id"
_DATE_COLUMN = "date"


@dataclass(frozen=True)
class WalkForwardWindow:
    window_id: str
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def generate_walk_forward_windows(
    *,
    date_min: str | pd.Timestamp,
    date_max: str | pd.Timestamp,
    train_years: int = 10,
    test_years: int = 1,
    step_years: int = 1,
    first_train_start: str | pd.Timestamp | None = None,
) -> list[WalkForwardWindow]:
    """Generate deterministic rolling walk-forward windows on month-end dates."""
    _validate_positive_int(train_years, "train_years")
    _validate_positive_int(test_years, "test_years")
    _validate_positive_int(step_years, "step_years")

    lower_bound = _parse_month_end(date_min, field_name="date_min")
    upper_bound = _parse_month_end(date_max, field_name="date_max")
    if lower_bound > upper_bound:
        raise ValueError("date_min must be on or before date_max")

    start_anchor = (
        _parse_month_end(first_train_start, field_name="first_train_start")
        if first_train_start is not None
        else lower_bound
    )

    windows: list[WalkForwardWindow] = []
    train_span_months = train_years * 12
    test_span_months = test_years * 12
    step_span_months = step_years * 12

    current_train_start = start_anchor
    while current_train_start <= upper_bound:
        train_end = _shift_months(current_train_start, train_span_months - 1)
        test_start = _shift_months(current_train_start, train_span_months)
        test_end = _shift_months(test_start, test_span_months - 1)

        if test_end > upper_bound:
            break

        if current_train_start >= lower_bound:
            windows.append(
                WalkForwardWindow(
                    window_id=_format_window_id(
                        train_start=current_train_start,
                        train_end=train_end,
                        test_start=test_start,
                        test_end=test_end,
                    ),
                    train_start=current_train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                )
            )

        current_train_start = _shift_months(current_train_start, step_span_months)

    return windows


def split_dataset_for_window(
    dataset: pd.DataFrame,
    window: WalkForwardWindow,
    *,
    date_col: str = "date",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a dataset into train/test frames for one walk-forward window."""
    frame = _normalize_dataset_frame(dataset, date_col=date_col)
    train_start = _parse_month_end(window.train_start, field_name="window.train_start")
    train_end = _parse_month_end(window.train_end, field_name="window.train_end")
    test_start = _parse_month_end(window.test_start, field_name="window.test_start")
    test_end = _parse_month_end(window.test_end, field_name="window.test_end")

    if train_start > train_end:
        raise ValueError("window train_start must be on or before train_end")
    if test_start > test_end:
        raise ValueError("window test_start must be on or before test_end")
    if train_end >= test_start:
        raise ValueError("train and test windows must not overlap")

    train_df = frame.loc[(frame[date_col] >= train_start) & (frame[date_col] <= train_end)].copy()
    test_df = frame.loc[(frame[date_col] >= test_start) & (frame[date_col] <= test_end)].copy()

    if train_df.empty:
        raise ValueError(f"Train split is empty for window {window.window_id}")
    if test_df.empty:
        raise ValueError(f"Test split is empty for window {window.window_id}")

    _validate_unique_asset_date(train_df, date_col=date_col, split_name="train")
    _validate_unique_asset_date(test_df, date_col=date_col, split_name="test")

    train_dates = set(train_df[date_col].dropna().unique().tolist())
    test_dates = set(test_df[date_col].dropna().unique().tolist())
    if train_dates.intersection(test_dates):
        raise ValueError(f"train and test windows overlap for window {window.window_id}")

    sort_columns = [date_col, _ASSET_ID_COLUMN]
    train_df = train_df.sort_values(sort_columns, kind="mergesort").reset_index(drop=True)
    test_df = test_df.sort_values(sort_columns, kind="mergesort").reset_index(drop=True)
    return train_df, test_df


def build_walk_forward_splits(
    dataset: pd.DataFrame,
    *,
    train_years: int = 10,
    test_years: int = 1,
    step_years: int = 1,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[tuple[WalkForwardWindow, pd.DataFrame, pd.DataFrame]]:
    """Build all walk-forward train/test splits from an existing CRSP ML dataset."""
    _validate_positive_int(train_years, "train_years")
    _validate_positive_int(test_years, "test_years")
    _validate_positive_int(step_years, "step_years")

    frame = _normalize_dataset_frame(dataset)

    start_dt = _parse_optional_month_end(start_date, field_name="start_date")
    end_dt = _parse_optional_month_end(end_date, field_name="end_date")
    if start_dt is not None and end_dt is not None and start_dt > end_dt:
        raise ValueError("start_date must be on or before end_date")

    if start_dt is not None:
        frame = frame.loc[frame[_DATE_COLUMN] >= start_dt]
    if end_dt is not None:
        frame = frame.loc[frame[_DATE_COLUMN] <= end_dt]

    if frame.empty:
        raise ValueError("Filtered dataset is empty")

    _validate_unique_asset_date(frame, date_col=_DATE_COLUMN, split_name="dataset")

    frame = frame.sort_values([_DATE_COLUMN, _ASSET_ID_COLUMN], kind="mergesort").reset_index(drop=True)

    windows = generate_walk_forward_windows(
        date_min=frame[_DATE_COLUMN].min(),
        date_max=frame[_DATE_COLUMN].max(),
        train_years=train_years,
        test_years=test_years,
        step_years=step_years,
    )
    if not windows:
        raise ValueError("No walk-forward windows fit within the filtered dataset date range")

    splits: list[tuple[WalkForwardWindow, pd.DataFrame, pd.DataFrame]] = []
    for window in windows:
        train_df, test_df = split_dataset_for_window(frame, window, date_col=_DATE_COLUMN)
        splits.append((window, train_df, test_df))
    return splits


def build_walk_forward_qc(
    splits: list[tuple[WalkForwardWindow, pd.DataFrame, pd.DataFrame]],
) -> dict[str, object]:
    """Build a QC payload for a list of walk-forward split outputs."""
    split_list = list(splits)
    if not split_list:
        return {
            "windows": 0,
            "total_train_rows": 0,
            "total_test_rows": 0,
            "first_train_start": None,
            "last_test_end": None,
            "train_years": None,
            "test_years": None,
            "step_years": None,
            "per_window": [],
        }

    per_window: list[dict[str, object]] = []
    total_train_rows = 0
    total_test_rows = 0
    for window, train_df, test_df in split_list:
        train_dates = pd.to_datetime(train_df[_DATE_COLUMN], errors="coerce")
        test_dates = pd.to_datetime(test_df[_DATE_COLUMN], errors="coerce")
        per_window.append(
            {
                "window_id": window.window_id,
                "train_start": _date_string(window.train_start),
                "train_end": _date_string(window.train_end),
                "test_start": _date_string(window.test_start),
                "test_end": _date_string(window.test_end),
                "train_rows": int(len(train_df)),
                "test_rows": int(len(test_df)),
                "train_assets": int(train_df[_ASSET_ID_COLUMN].nunique(dropna=True)),
                "test_assets": int(test_df[_ASSET_ID_COLUMN].nunique(dropna=True)),
                "train_months": int(train_dates.dt.to_period("M").nunique()),
                "test_months": int(test_dates.dt.to_period("M").nunique()),
                "train_duplicate_asset_date_rows": int(
                    train_df[[_ASSET_ID_COLUMN, _DATE_COLUMN]].duplicated().sum()
                ),
                "test_duplicate_asset_date_rows": int(
                    test_df[[_ASSET_ID_COLUMN, _DATE_COLUMN]].duplicated().sum()
                ),
            }
        )
        total_train_rows += len(train_df)
        total_test_rows += len(test_df)

    first_window = split_list[0][0]
    last_window = split_list[-1][0]

    return {
        "windows": int(len(split_list)),
        "total_train_rows": int(total_train_rows),
        "total_test_rows": int(total_test_rows),
        "first_train_start": _date_string(first_window.train_start),
        "last_test_end": _date_string(last_window.test_end),
        "train_years": _infer_year_span(first_window.train_start, first_window.train_end),
        "test_years": _infer_year_span(first_window.test_start, first_window.test_end),
        "step_years": _infer_step_years(split_list),
        "per_window": per_window,
    }


def _normalize_dataset_frame(dataset: pd.DataFrame, *, date_col: str = _DATE_COLUMN) -> pd.DataFrame:
    if date_col not in dataset.columns:
        raise ValueError(f"Missing required date column: {date_col!r}")
    if _ASSET_ID_COLUMN not in dataset.columns:
        raise ValueError("Missing required asset_id column: 'asset_id'")

    frame = dataset.copy()
    frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    if frame[date_col].isna().any():
        invalid_values = frame.loc[frame[date_col].isna(), date_col].astype(str).head(5).tolist()
        raise ValueError(f"{date_col} must be parseable as datetime; invalid values: {invalid_values}")
    frame[date_col] = (frame[date_col] + pd.offsets.MonthEnd(0)).dt.normalize()

    if frame[_ASSET_ID_COLUMN].isna().any():
        raise ValueError("asset_id must be non-null")
    if frame[_ASSET_ID_COLUMN].astype("string").str.strip().eq("").any():
        raise ValueError("asset_id must be non-null")
    frame[_ASSET_ID_COLUMN] = frame[_ASSET_ID_COLUMN].astype(str)
    return frame


def _validate_unique_asset_date(frame: pd.DataFrame, *, date_col: str, split_name: str) -> None:
    if frame[[_ASSET_ID_COLUMN, date_col]].duplicated().any():
        raise ValueError(f"duplicate asset_id/date rows are not allowed in {split_name} split")


def _validate_positive_int(value: int, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be > 0")


def _parse_optional_month_end(value: str | None, *, field_name: str) -> pd.Timestamp | None:
    if value is None:
        return None
    return _parse_month_end(value, field_name=field_name)


def _parse_month_end(value: str | pd.Timestamp, *, field_name: str) -> pd.Timestamp:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"{field_name} must be parseable as datetime: {value!r}")
    return (pd.Timestamp(parsed) + pd.offsets.MonthEnd(0)).normalize()


def _shift_months(value: pd.Timestamp, months: int) -> pd.Timestamp:
    return (pd.Timestamp(value) + pd.DateOffset(months=months)).normalize()


def _date_string(value: pd.Timestamp) -> str:
    return pd.Timestamp(value).date().isoformat()


def _months_between(start: pd.Timestamp, end: pd.Timestamp) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def _infer_year_span(start: pd.Timestamp, end: pd.Timestamp) -> int | None:
    months = _months_between(start, end) + 1
    if months <= 0 or months % 12 != 0:
        return None
    return int(months // 12)


def _infer_step_years(splits: list[tuple[WalkForwardWindow, pd.DataFrame, pd.DataFrame]]) -> int | None:
    if len(splits) < 2:
        return None

    step_months = _months_between(splits[0][0].train_start, splits[1][0].train_start)
    if step_months <= 0 or step_months % 12 != 0:
        return None
    for left, right in zip(splits, splits[1:], strict=False):
        if _months_between(left[0].train_start, right[0].train_start) != step_months:
            return None
    return int(step_months // 12)


def _format_window_id(
    *,
    train_start: pd.Timestamp,
    train_end: pd.Timestamp,
    test_start: pd.Timestamp,
    test_end: pd.Timestamp,
) -> str:
    train_span = _format_year_span(train_start, train_end)
    test_span = _format_year_span(test_start, test_end)
    return f"train_{train_span}_test_{test_span}"


def _format_year_span(start: pd.Timestamp, end: pd.Timestamp) -> str:
    if start.year == end.year:
        return str(start.year)
    return f"{start.year}-{end.year}"
