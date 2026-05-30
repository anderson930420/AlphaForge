from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_return_panel(path: Path | str) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file format: {suffix}. Use .csv or .parquet")


def build_forward_return_labels(
    returns_df: pd.DataFrame,
    *,
    asset_id_col: str = "asset_id",
    date_col: str = "date",
    return_col: str = "ret",
    delisting_return_col: str | None = None,
    horizon_months: int = 1,
    label_col: str | None = None,
    source: str = "local_returns",
) -> pd.DataFrame:
    if horizon_months < 1:
        raise ValueError("horizon_months must be >= 1")
    if returns_df.empty:
        raise ValueError("Empty return panel")
    required = {asset_id_col, date_col, return_col}
    missing = required - set(returns_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if label_col is None:
        label_col = f"ret_fwd_{horizon_months}m"

    df = returns_df.copy()
    df[asset_id_col] = df[asset_id_col].astype(str)
    df["_orig_date"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["_orig_date"])
    if df.empty:
        raise ValueError("No valid date rows after parsing")
    df = df.copy()
    df["date"] = df["_orig_date"] + pd.offsets.MonthEnd(0)
    if delisting_return_col is not None:
        if delisting_return_col not in df.columns:
            raise ValueError(f"Delisting return column '{delisting_return_col}' not found in data")
        df[return_col] = pd.to_numeric(df[return_col], errors="coerce")
        df[delisting_return_col] = pd.to_numeric(df[delisting_return_col], errors="coerce")
        ret = df[return_col].fillna(0.0)
        dlret = df[delisting_return_col].fillna(0.0)
        combined = (1 + ret) * (1 + dlret) - 1
        mask_both_missing = df[return_col].isna() & df[delisting_return_col].isna()
        combined = combined.where(~mask_both_missing, other=float("nan"))
        df["_combined_ret"] = combined
    else:
        df["_combined_ret"] = pd.to_numeric(df[return_col], errors="coerce")
    df = df.sort_values([asset_id_col, "date"]).reset_index(drop=True)
    df["_target_date"] = df["date"] + pd.offsets.MonthEnd(horizon_months)

    target_returns = (
        df[[asset_id_col, "date", "_combined_ret"]]
        .drop_duplicates(subset=[asset_id_col, "date"], keep="last")
        .rename(columns={"date": "_target_date", "_combined_ret": label_col})
    )

    result_df = df[[asset_id_col, "date", "_target_date"]].merge(
        target_returns,
        on=[asset_id_col, "_target_date"],
        how="left",
        sort=False,
    )
    result_df = result_df.dropna(subset=[label_col]).copy()
    if result_df.empty:
        columns = ["asset_id", "date", "target_date", "horizon_months", label_col, "source"]
        return pd.DataFrame(columns=columns)

    result_df = result_df.rename(columns={asset_id_col: "asset_id", "_target_date": "target_date"})
    result_df["horizon_months"] = horizon_months
    result_df["source"] = source
    return result_df[["asset_id", "date", "target_date", "horizon_months", label_col, "source"]].reset_index(drop=True)


def join_features_with_return_labels(
    features_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    *,
    asset_id_col: str = "asset_id",
    date_col: str = "date",
) -> pd.DataFrame:
    feat = features_df.copy()
    feat[asset_id_col] = feat[asset_id_col].astype(str)
    feat["_orig_date"] = pd.to_datetime(feat[date_col], errors="coerce")
    feat = feat.dropna(subset=["_orig_date"])
    if feat.empty:
        raise ValueError("No valid date rows in features after parsing")
    feat = feat.copy()
    feat[date_col] = feat["_orig_date"] + pd.offsets.MonthEnd(0)
    lbl = labels_df.copy()
    lbl[asset_id_col] = lbl[asset_id_col].astype(str)
    lbl["_orig_date"] = pd.to_datetime(lbl[date_col], errors="coerce")
    lbl = lbl.dropna(subset=["_orig_date"])
    lbl = lbl.copy()
    lbl[date_col] = lbl["_orig_date"] + pd.offsets.MonthEnd(0)
    joined = feat.merge(lbl, on=[asset_id_col, date_col], how="inner")
    helper_cols = [c for c in joined.columns if c.startswith("_orig_date")]
    return joined.drop(columns=helper_cols)
