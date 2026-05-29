from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


OAP_MULTIFACTOR_SIGNAL_COLUMNS = (
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


@dataclass
class FeatureSpec:
    name: str
    weight: float = 1.0
    higher_is_better: bool = True


@dataclass
class OAPMultiFactorConfig:
    version: str = "alphaforge_oap_multifactor_v0.1"
    signal_name: str = "oap_multifactor_score"
    date_col: str = "date"
    asset_id_col: str = "asset_id"
    features: list[FeatureSpec] = field(default_factory=list)
    long_quantile: float = 0.8
    short_quantile: float = 0.2
    gross_long_weight: float = 1.0
    gross_short_weight: float = -1.0
    missing_policy: str = "ignore_feature"
    normalization: str = "zscore_by_date"

    @classmethod
    def from_yaml(cls, path: Path | str) -> "OAPMultiFactorConfig":
        path = Path(path)
        raw = yaml.safe_load(path.read_text())
        features = []
        for f in raw.get("features", []):
            features.append(FeatureSpec(**f))
        return cls(
            version=raw.get("version", cls.version),
            signal_name=raw.get("signal_name", cls.signal_name),
            date_col=raw.get("date_col", cls.date_col),
            asset_id_col=raw.get("asset_id_col", cls.asset_id_col),
            features=features,
            long_quantile=raw.get("long_quantile", cls.long_quantile),
            short_quantile=raw.get("short_quantile", cls.short_quantile),
            gross_long_weight=raw.get("gross_long_weight", cls.gross_long_weight),
            gross_short_weight=raw.get("gross_short_weight", cls.gross_short_weight),
            missing_policy=raw.get("missing_policy", cls.missing_policy),
            normalization=raw.get("normalization", cls.normalization),
        )


def load_feature_panel(path: Path | str, date_col: str = "date", asset_id_col: str = "asset_id") -> pd.DataFrame:
    path = Path(path)
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    required = [date_col, asset_id_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in feature panel: {missing}")
    return df


def build_multifactor_signal(
    features_df: pd.DataFrame,
    config: OAPMultiFactorConfig,
    source: str = "OpenAssetPricing",
) -> pd.DataFrame:
    feature_names = [f.name for f in config.features]
    for fname in feature_names:
        if fname not in features_df.columns:
            raise ValueError(f"Configured feature {fname!r} not found in feature panel columns: {list(features_df.columns)}")

    frame = features_df[[config.date_col, config.asset_id_col] + feature_names].copy()
    frame.rename(columns={config.date_col: "datetime", config.asset_id_col: "asset_id"}, inplace=True)
    frame["datetime"] = _normalize_daily_dates(frame["datetime"])
    frame["available_at"] = frame["datetime"].copy()
    frame["symbol"] = frame["asset_id"].astype(str)

    output_parts = []
    for date, group in frame.groupby("datetime", sort=True, group_keys=False):
        scored = _build_date_score(group, config, feature_names)
        output_parts.append(scored)

    if not output_parts:
        return _empty_signal_frame()

    output = pd.concat(output_parts, ignore_index=True)
    output["source"] = source
    output = output.reindex(columns=OAP_MULTIFACTOR_SIGNAL_COLUMNS)
    return output.sort_values(["datetime", "symbol"]).reset_index(drop=True)


def _build_date_score(group: pd.DataFrame, config: OAPMultiFactorConfig, feature_names: list[str]) -> pd.DataFrame:
    weights: list[float] = []
    normalized_values: list[pd.Series] = []

    for fspec in config.features:
        col = fspec.name
        values = pd.to_numeric(group[col], errors="coerce")
        valid = values.notna()
        if not valid.any():
            continue

        mu = values.loc[valid].mean()
        sigma = values.loc[valid].std(ddof=1)
        if sigma == 0 or pd.isna(sigma):
            norm = pd.Series(0.0, index=values.index)
        else:
            norm = (values - mu) / sigma

        if not fspec.higher_is_better:
            norm = -norm

        weights.append(fspec.weight)
        normalized_values.append(norm)

    if not normalized_values:
        result = group.copy()
        result["score"] = float("nan")
        result["signal_name"] = config.signal_name
        result["direction"] = 0
        result["target_weight"] = 0.0
        result["source"] = "OpenAssetPricing"
        return result

    total_weight = sum(weights)
    weighted_sum = sum(w * v for w, v in zip(weights, normalized_values)) / total_weight

    result = group.copy()
    result["score"] = weighted_sum
    result["signal_name"] = config.signal_name

    score_series = result["score"].copy()
    long_thresh = score_series.quantile(config.long_quantile)
    short_thresh = score_series.quantile(config.short_quantile)

    result["direction"] = 0
    result.loc[score_series >= long_thresh, "direction"] = 1
    result.loc[score_series <= short_thresh, "direction"] = -1

    result["target_weight"] = 0.0
    long_mask = result["direction"].eq(1)
    short_mask = result["direction"].eq(-1)

    if long_mask.any():
        result.loc[long_mask, "target_weight"] = config.gross_long_weight / int(long_mask.sum())
    if short_mask.any():
        result.loc[short_mask, "target_weight"] = config.gross_short_weight / int(short_mask.sum())

    return result


def _normalize_daily_dates(values: pd.Series) -> pd.Series:
    def normalize(value: object) -> pd.Timestamp:
        if pd.isna(value):
            return pd.NaT
        try:
            parsed = pd.to_datetime(value, errors="raise")
        except (TypeError, ValueError):
            return pd.NaT
        return pd.Timestamp(parsed.date())
    return values.map(normalize)


def _empty_signal_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=OAP_MULTIFACTOR_SIGNAL_COLUMNS)
