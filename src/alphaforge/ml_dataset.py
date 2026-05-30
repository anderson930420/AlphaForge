from __future__ import annotations

import pandas as pd


_METADATA_EXCLUDE = {"asset_id", "date", "target_date", "horizon_months", "source"}
_DEFAULT_EXCLUDE_PREFIXES = ("ret_fwd", "prediction", "predicted", "output")


def infer_ml_feature_cols(
    panel_df: pd.DataFrame,
    *,
    asset_id_col: str = "asset_id",
    date_col: str = "date",
    label_col: str = "ret_fwd_1m",
    exclude_prefixes: tuple[str, ...] = _DEFAULT_EXCLUDE_PREFIXES,
) -> list[str]:
    """Infer numeric ML feature columns while excluding leakage-prone fields.

    This is the shared feature inference contract for AlphaForge ML datasets,
    sklearn adapters, and torch adapters. It intentionally excludes forward
    return labels and model-output-like columns so prior predictions cannot
    silently leak back into a later model fit.
    """
    exclude = _METADATA_EXCLUDE | {asset_id_col, date_col, label_col}
    normalized_prefixes = tuple(prefix.lower() for prefix in exclude_prefixes)

    return [
        col for col in panel_df.columns
        if col not in exclude
        and not col.lower().startswith(normalized_prefixes)
        and pd.api.types.is_numeric_dtype(panel_df[col])
    ]


def build_ml_dataset(
    panel_df: pd.DataFrame,
    *,
    asset_id_col: str = "asset_id",
    date_col: str = "date",
    label_col: str = "ret_fwd_1m",
    feature_cols: list[str] | None = None,
    drop_missing_label: bool = True,
    drop_missing_features: bool = False,
) -> pd.DataFrame:
    required = {asset_id_col, date_col, label_col}
    missing = required - set(panel_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = panel_df.copy()

    df[asset_id_col] = df[asset_id_col].astype(str)
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    df[date_col] = df[date_col] + pd.offsets.MonthEnd(0)

    if feature_cols is None:
        feature_cols = infer_ml_feature_cols(
            df,
            asset_id_col=asset_id_col,
            date_col=date_col,
            label_col=label_col,
        )

    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df[label_col] = pd.to_numeric(df[label_col], errors="coerce")

    if drop_missing_label:
        df = df.dropna(subset=[label_col])

    if drop_missing_features:
        df = df.dropna(subset=feature_cols)

    columns = [asset_id_col, date_col] + feature_cols + [label_col]
    return df[columns].reset_index(drop=True)


def time_train_test_split(
    dataset_df: pd.DataFrame,
    *,
    date_col: str = "date",
    train_end: str | None = None,
    test_start: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_end_dt = pd.Timestamp(train_end) + pd.offsets.MonthEnd(0) if train_end is not None else None
    test_start_dt = pd.Timestamp(test_start) + pd.offsets.MonthEnd(0) if test_start is not None else None

    df = dataset_df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce") + pd.offsets.MonthEnd(0)

    if train_end_dt is None and test_start_dt is None:
        raise ValueError("At least one of train_end or test_start must be provided")

    if train_end_dt is not None and test_start_dt is not None:
        train_df = df[df[date_col] <= train_end_dt]
        test_df = df[df[date_col] >= test_start_dt]
    elif train_end_dt is not None:
        train_df = df[df[date_col] <= train_end_dt]
        test_df = df[df[date_col] > train_end_dt]
    else:
        test_df = df[df[date_col] >= test_start_dt]
        train_df = df[df[date_col] < test_start_dt]

    if train_df.empty:
        raise ValueError("Train set is empty")
    if test_df.empty:
        raise ValueError("Test set is empty")

    return train_df.reset_index(drop=True), test_df.reset_index(drop=True)
