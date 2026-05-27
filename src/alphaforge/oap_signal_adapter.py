from __future__ import annotations

import pandas as pd

from alphaforge.oap_factor_contract import OAPFactorContract
from alphaforge.open_asset_pricing import OAP_SIGNAL_COLUMNS


class OAPSignalAdapterError(ValueError):
    pass


def build_oap_signal_frame_from_factor_frame(
    factor_frame: pd.DataFrame,
    contract: OAPFactorContract,
    *,
    signal_name: str | None = None,
) -> pd.DataFrame:
    _validate_factor_frame_columns(factor_frame)
    _validate_contract_subset(contract)

    frame = factor_frame.copy()
    frame["datetime"] = _normalize_daily_dates(frame["datetime"], "datetime")
    frame["available_at"] = _normalize_daily_dates(frame["available_at"], "available_at")
    frame["symbol"] = frame["symbol"].astype(str)
    frame["factor_name"] = frame["factor_name"].astype(str)
    frame["factor_value"] = pd.to_numeric(frame["factor_value"], errors="raise")
    frame["source"] = frame["source"].astype(str)

    _validate_factor_frame_matches_contract(frame, contract)

    output = pd.DataFrame(
        {
            "datetime": frame["datetime"],
            "available_at": frame["available_at"],
            "symbol": frame["symbol"],
            "signal_name": signal_name or f"oap_{contract.factor['name']}",
            "score": frame["factor_value"],
            "direction": _build_threshold_direction(frame["factor_value"], contract),
            "source": frame["source"],
        }
    )
    output["target_weight"] = _build_signed_unit_target_weight(output["direction"], contract)
    output = output.reindex(columns=OAP_SIGNAL_COLUMNS)
    _validate_signal_frame(output)
    return output.sort_values(["datetime", "symbol"]).reset_index(drop=True)


def _validate_factor_frame_columns(frame: pd.DataFrame) -> None:
    required = ["datetime", "available_at", "symbol", "factor_name", "factor_value", "source"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise OAPSignalAdapterError(f"Missing required normalized OAP factor columns: {missing}")


def _validate_contract_subset(contract: OAPFactorContract) -> None:
    if contract.decision_rule.get("type") != "threshold":
        raise OAPSignalAdapterError(f"Unsupported decision_rule.type: {contract.decision_rule.get('type')!r}")
    if contract.weighting.get("target_weight_mode") != "signed_unit":
        raise OAPSignalAdapterError(
            f"Unsupported weighting.target_weight_mode: {contract.weighting.get('target_weight_mode')!r}"
        )


def _validate_factor_frame_matches_contract(frame: pd.DataFrame, contract: OAPFactorContract) -> None:
    expected_factor_name = str(contract.factor["name"])
    factor_names = set(frame["factor_name"].dropna().astype(str).unique())
    if factor_names != {expected_factor_name}:
        raise OAPSignalAdapterError(
            f"normalized factor frame must contain exactly factor_name {expected_factor_name!r}; got {sorted(factor_names)}"
        )
    if frame["datetime"].isna().any():
        raise OAPSignalAdapterError("datetime is required")
    if frame["available_at"].isna().any():
        raise OAPSignalAdapterError("available_at is required")
    if frame["symbol"].isna().any() or frame["symbol"].astype(str).eq("").any():
        raise OAPSignalAdapterError("symbol is required")
    if frame["factor_value"].isna().any():
        raise OAPSignalAdapterError("factor_value is required")
    if frame.duplicated(subset=["datetime", "symbol", "factor_name"]).any():
        raise OAPSignalAdapterError("duplicate datetime-symbol-factor_name rows are not allowed")


def _build_threshold_direction(values: pd.Series, contract: OAPFactorContract) -> pd.Series:
    long_threshold = float(contract.decision_rule["long_threshold"])
    short_threshold = float(contract.decision_rule["short_threshold"])
    direction = pd.Series(0, index=values.index, dtype=int)
    direction.loc[values > long_threshold] = 1
    direction.loc[values < short_threshold] = -1
    return direction


def _build_signed_unit_target_weight(direction: pd.Series, contract: OAPFactorContract) -> pd.Series:
    weighting = contract.weighting
    target_weight = pd.Series(float(weighting["neutral_weight"]), index=direction.index, dtype=float)
    target_weight.loc[direction.eq(1)] = float(weighting["long_weight"])
    target_weight.loc[direction.eq(-1)] = float(weighting["short_weight"])
    return target_weight


def _normalize_daily_dates(values: pd.Series, field_name: str) -> pd.Series:
    def normalize(value: object) -> pd.Timestamp:
        if pd.isna(value):
            return pd.NaT
        try:
            parsed = pd.to_datetime(value, errors="raise")
        except (TypeError, ValueError) as exc:
            raise OAPSignalAdapterError(f"Could not parse {field_name} value {value!r}") from exc
        return pd.Timestamp(parsed.date())

    return values.map(normalize)


def _validate_signal_frame(frame: pd.DataFrame) -> None:
    if frame["score"].isna().any():
        raise OAPSignalAdapterError("score is required")
    if not frame["direction"].isin([-1, 0, 1]).all():
        raise OAPSignalAdapterError("direction must be ternary: -1, 0, or 1")
    if frame["target_weight"].isna().any():
        raise OAPSignalAdapterError("target_weight is required")
    if (frame["target_weight"] < -1.0).any() or (frame["target_weight"] > 1.0).any():
        raise OAPSignalAdapterError("target_weight must be within [-1.0, 1.0]")
