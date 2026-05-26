"""Open Asset Pricing adapter utilities.

This module does not download Open Asset Pricing data. It converts an already
loaded Open Asset Pricing-like firm-characteristic DataFrame into AlphaForge's
v0.2 signal.csv contract.

The expected upstream shape is intentionally lightweight and column-mapped:
date, asset id, and one characteristic score column.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


OAP_SIGNAL_COLUMNS = (
    "datetime",
    "available_at",
    "symbol",
    "signal_name",
    "score",
    "direction",
    "target_weight",
    "source",
)


@dataclass(frozen=True)
class OAPQuantilePolicy:
    """Cross-sectional long/short policy for signed characteristics."""

    long_quantile: float = 0.8
    short_quantile: float = 0.2
    gross_long_weight: float = 1.0
    gross_short_weight: float = -1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.short_quantile < self.long_quantile <= 1.0:
            raise ValueError("short_quantile must be < long_quantile and both must be within [0, 1]")
        if self.gross_long_weight <= 0.0:
            raise ValueError("gross_long_weight must be positive")
        if self.gross_short_weight >= 0.0:
            raise ValueError("gross_short_weight must be negative")
        if abs(self.gross_long_weight) > 1.0 or abs(self.gross_short_weight) > 1.0:
            raise ValueError("gross leg weights must stay within no-leverage bounds [-1, 1]")


def build_oap_v02_signal_frame(
    characteristics: pd.DataFrame,
    *,
    characteristic: str,
    date_col: str = "date",
    asset_id_col: str = "asset_id",
    available_at_col: str | None = None,
    signal_name: str | None = None,
    source: str = "OpenAssetPricing",
    policy: OAPQuantilePolicy | None = None,
    invert_score: bool = False,
) -> pd.DataFrame:
    """Convert characteristic values into AlphaForge v0.2 signal rows.

    Open Asset Pricing characteristics are commonly used cross-sectionally:
    high signed characteristic values are long candidates and low values are
    short candidates. This adapter maps each rebalance date into top/bottom
    quantile target weights.
    """
    resolved_policy = policy or OAPQuantilePolicy()
    _validate_input_columns(characteristics, characteristic, date_col, asset_id_col, available_at_col)

    frame = characteristics[[date_col, asset_id_col, characteristic]].copy()
    frame.rename(columns={date_col: "datetime", asset_id_col: "symbol", characteristic: "score"}, inplace=True)
    frame["available_at"] = (
        characteristics[available_at_col].copy() if available_at_col is not None else frame["datetime"].copy()
    )
    frame["datetime"] = _normalize_daily_dates(frame["datetime"], "datetime")
    frame["available_at"] = _normalize_daily_dates(frame["available_at"], "available_at")
    frame["symbol"] = frame["symbol"].astype(str)
    frame["score"] = pd.to_numeric(frame["score"], errors="raise")
    if invert_score:
        frame["score"] = -frame["score"]

    _validate_normalized_frame(frame)
    frame["signal_name"] = signal_name or f"oap_{characteristic}"
    frame["source"] = source

    output_parts = [
        _apply_quantile_policy(group, resolved_policy)
        for _, group in frame.groupby("datetime", sort=True, group_keys=False)
    ]
    output = pd.concat(output_parts, ignore_index=True) if output_parts else _empty_signal_frame()
    output = output.reindex(columns=OAP_SIGNAL_COLUMNS)
    return output.sort_values(["datetime", "symbol"]).reset_index(drop=True)


def _apply_quantile_policy(group: pd.DataFrame, policy: OAPQuantilePolicy) -> pd.DataFrame:
    result = group.copy()
    long_threshold = result["score"].quantile(policy.long_quantile)
    short_threshold = result["score"].quantile(policy.short_quantile)

    result["direction"] = 0
    result.loc[result["score"] >= long_threshold, "direction"] = 1
    result.loc[result["score"] <= short_threshold, "direction"] = -1

    long_mask = result["direction"].eq(1)
    short_mask = result["direction"].eq(-1)

    result["target_weight"] = 0.0
    if long_mask.any():
        result.loc[long_mask, "target_weight"] = policy.gross_long_weight / int(long_mask.sum())
    if short_mask.any():
        result.loc[short_mask, "target_weight"] = policy.gross_short_weight / int(short_mask.sum())

    return result


def _validate_input_columns(
    frame: pd.DataFrame,
    characteristic: str,
    date_col: str,
    asset_id_col: str,
    available_at_col: str | None,
) -> None:
    required = [date_col, asset_id_col, characteristic]
    if available_at_col is not None:
        required.append(available_at_col)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required Open Asset Pricing columns: {missing}")


def _validate_normalized_frame(frame: pd.DataFrame) -> None:
    if frame["datetime"].isna().any():
        raise ValueError("datetime is required")
    if frame["available_at"].isna().any():
        raise ValueError("available_at is required")
    if frame["symbol"].isna().any():
        raise ValueError("symbol is required")
    if frame["score"].isna().any():
        raise ValueError("score is required")
    if (frame["available_at"] > frame["datetime"]).any():
        raise ValueError("available_at must be less than or equal to datetime")
    if frame.duplicated(subset=["datetime", "symbol"]).any():
        raise ValueError("duplicate datetime-symbol characteristic rows are not allowed")


def _normalize_daily_dates(values: pd.Series, field_name: str) -> pd.Series:
    def normalize(value: object) -> pd.Timestamp:
        if pd.isna(value):
            return pd.NaT
        try:
            parsed = pd.to_datetime(value, errors="raise")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Could not parse {field_name} value {value!r}") from exc
        return pd.Timestamp(parsed.date())

    return values.map(normalize)


def _empty_signal_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=OAP_SIGNAL_COLUMNS)
