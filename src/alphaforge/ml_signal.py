from __future__ import annotations

from pathlib import Path

import pandas as pd


ML_SIGNAL_SIGNAL_COLUMNS = (
    "datetime",
    "available_at",
    "symbol",
    "asset_id",
    "signal_name",
    "score",
    "direction",
    "target_weight",
    "source",
)


def load_prediction_panel(path: Path | str) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported prediction file suffix: {suffix!r}. Supported suffixes: .csv, .parquet")


def build_ml_prediction_signal(
    predictions_df: pd.DataFrame,
    *,
    asset_id_col: str = "asset_id",
    date_col: str = "date",
    prediction_col: str = "predicted_return",
    symbol_col: str | None = None,
    signal_name: str = "ml_predicted_return",
    source: str = "AlphaForgeML",
    long_quantile: float = 0.8,
    short_quantile: float = 0.2,
    gross_long_weight: float = 1.0,
    gross_short_weight: float = -1.0,
    available_at_col: str | None = None,
) -> pd.DataFrame:
    required = {asset_id_col, date_col, prediction_col}
    missing = required - set(predictions_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if predictions_df.empty:
        raise ValueError("Prediction panel is empty")

    if not (0 <= short_quantile <= 1):
        raise ValueError(f"short_quantile must be between 0 and 1, got {short_quantile}")
    if not (0 <= long_quantile <= 1):
        raise ValueError(f"long_quantile must be between 0 and 1, got {long_quantile}")
    if short_quantile >= long_quantile:
        raise ValueError(
            f"short_quantile ({short_quantile}) must be less than long_quantile ({long_quantile})"
        )

    frame = predictions_df[[asset_id_col, date_col, prediction_col]].copy()
    if symbol_col is not None and symbol_col in predictions_df.columns:
        frame["symbol"] = predictions_df[symbol_col].copy()
    else:
        frame["symbol"] = frame[asset_id_col].astype(str)

    frame[date_col] = _normalize_to_month_end(frame[date_col])
    frame = frame.dropna(subset=[date_col])
    if frame.empty:
        raise ValueError("Prediction panel has no valid dates after parsing")

    frame.rename(columns={date_col: "datetime"}, inplace=True)
    frame["score"] = pd.to_numeric(frame[prediction_col], errors="coerce")

    if available_at_col is not None and available_at_col in predictions_df.columns:
        available_raw = predictions_df[available_at_col].copy()
        frame["available_at"] = _normalize_to_month_end(available_raw)
    else:
        frame["available_at"] = frame["datetime"].copy()

    frame["signal_name"] = signal_name
    frame["asset_id"] = frame[asset_id_col].astype(str)

    output_parts = []
    for date_val, group in frame.groupby("datetime", sort=True, group_keys=False):
        scored = _build_date_signal(group, long_quantile, short_quantile, gross_long_weight, gross_short_weight)
        output_parts.append(scored)

    if not output_parts:
        raise ValueError("No valid dates remain after groupby")

    output = pd.concat(output_parts, ignore_index=True)
    output["source"] = source

    output = output.reindex(columns=ML_SIGNAL_SIGNAL_COLUMNS)
    return output.sort_values(["datetime", "symbol"]).reset_index(drop=True)


def _build_date_signal(
    group: pd.DataFrame,
    long_quantile: float,
    short_quantile: float,
    gross_long_weight: float,
    gross_short_weight: float,
) -> pd.DataFrame:
    result = group.copy()
    result["direction"] = 0
    result["target_weight"] = 0.0

    score_valid = result["score"].notna()
    if not score_valid.any():
        return result

    score_series = result.loc[score_valid, "score"]
    if len(score_series) < 2:
        return result

    if score_series.nunique() < 2:
        return result

    long_thresh = score_series.quantile(long_quantile)
    short_thresh = score_series.quantile(short_quantile)

    if long_thresh <= short_thresh:
        return result

    long_mask = score_valid & (result["score"] >= long_thresh)
    short_mask = score_valid & (result["score"] <= short_thresh)

    result.loc[long_mask, "direction"] = 1
    result.loc[short_mask, "direction"] = -1

    if long_mask.any():
        result.loc[long_mask, "target_weight"] = gross_long_weight / int(long_mask.sum())
    if short_mask.any():
        result.loc[short_mask, "target_weight"] = gross_short_weight / int(short_mask.sum())

    return result


def _normalize_to_month_end(values: pd.Series) -> pd.Series:
    def normalize(value: object) -> pd.Timestamp:
        if pd.isna(value):
            return pd.NaT
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return pd.NaT
        return parsed + pd.offsets.MonthEnd(0)
    return values.map(normalize)
