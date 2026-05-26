"""External signal-file validation for the custom-signal workflow.

This module owns the file contract for precomputed signal inputs. It does not
compute signals, import external strategy internals, or change execution
semantics.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


COMMON_SIGNAL_COLUMNS = (
    "datetime",
    "available_at",
    "symbol",
    "signal_name",
    "source",
)
V1_SIGNAL_COLUMNS = COMMON_SIGNAL_COLUMNS + (
    "signal_value",
    "signal_binary",
)
V2_SIGNAL_COLUMNS = COMMON_SIGNAL_COLUMNS + (
    "score",
    "direction",
    "target_weight",
)
REQUIRED_SIGNAL_COLUMNS = V1_SIGNAL_COLUMNS
MISSING_SIGNAL_POLICY = "flat"
SIGNAL_CONTRACT_V1 = "v0.1"
SIGNAL_CONTRACT_V2 = "v0.2"
TARGET_COLUMN_BY_CONTRACT_VERSION = {
    SIGNAL_CONTRACT_V1: "signal_binary",
    SIGNAL_CONTRACT_V2: "target_weight",
}


def load_custom_signal_positions(
    signal_file: Path | str,
    market_data: pd.DataFrame,
    symbol: str | None = None,
    signal_name: str | None = None,
) -> tuple[pd.Series, dict[str, object]]:
    signal_frame, contract_version = _load_signal_frame(signal_file)
    signal_frame = _coerce_signal_frame(signal_frame, contract_version)
    signal_frame, selected_signal_name = _select_signal_name(signal_frame, signal_name)
    target_symbol = _resolve_target_symbol(signal_frame, market_data, symbol)
    signal_frame = _filter_and_validate_symbol(signal_frame, target_symbol)
    market_datetimes = _extract_market_datetimes(market_data)
    _validate_market_alignment(signal_frame, market_datetimes)

    target_column = TARGET_COLUMN_BY_CONTRACT_VERSION[contract_version]
    target_by_datetime = signal_frame.set_index("datetime")[target_column].astype(float)
    target_position = target_by_datetime.reindex(market_datetimes, fill_value=0.0).astype(float)
    target_position = pd.Series(target_position.to_numpy(dtype=float), index=market_data.index, name="target_position")

    metadata: dict[str, object] = {
        "symbol": target_symbol,
        "signal_row_count": int(len(signal_frame)),
        "missing_signal_policy": MISSING_SIGNAL_POLICY,
        "signal_contract_version": contract_version,
        "target_position_source_column": target_column,
    }
    if selected_signal_name is not None:
        metadata["signal_name"] = selected_signal_name
    source = _optional_single_unique_value(signal_frame["source"], "source", on_multiple="omit")
    if source is not None:
        metadata["source"] = source
    return target_position, metadata


def _load_signal_frame(signal_file: Path | str) -> tuple[pd.DataFrame, str]:
    signal_path = Path(signal_file)
    frame = pd.read_csv(signal_path)
    renamed = frame.rename(columns={name: name.strip().lower() for name in frame.columns})
    contract_version = _detect_signal_contract_version(renamed)
    required_columns = V2_SIGNAL_COLUMNS if contract_version == SIGNAL_CONTRACT_V2 else V1_SIGNAL_COLUMNS
    missing = [column for column in required_columns if column not in renamed.columns]
    if missing:
        raise ValueError(f"Missing required {contract_version} signal columns: {missing}")
    return renamed[list(required_columns)].copy(), contract_version


def _detect_signal_contract_version(frame: pd.DataFrame) -> str:
    if "target_weight" in frame.columns:
        return SIGNAL_CONTRACT_V2
    return SIGNAL_CONTRACT_V1


def _coerce_signal_frame(signal_frame: pd.DataFrame, contract_version: str) -> pd.DataFrame:
    cleaned = signal_frame.copy()
    cleaned["datetime"] = _normalize_daily_datetimes(cleaned["datetime"])
    cleaned["available_at"] = _normalize_daily_datetimes(cleaned["available_at"])

    if contract_version == SIGNAL_CONTRACT_V2:
        cleaned["score"] = pd.to_numeric(cleaned["score"], errors="raise")
        cleaned["direction"] = pd.to_numeric(cleaned["direction"], errors="raise")
        cleaned["target_weight"] = pd.to_numeric(cleaned["target_weight"], errors="raise")
    else:
        cleaned["signal_binary"] = pd.to_numeric(cleaned["signal_binary"], errors="raise")

    if cleaned["datetime"].isna().any():
        raise ValueError("datetime is required")
    if cleaned["available_at"].isna().any():
        raise ValueError("available_at is required")
    if cleaned["symbol"].isna().any():
        raise ValueError("symbol is required")
    if contract_version == SIGNAL_CONTRACT_V2:
        _validate_v02_signal_columns(cleaned)
    else:
        _validate_v01_signal_columns(cleaned)
    if cleaned.duplicated(subset=["datetime", "symbol", "signal_name"]).any():
        raise ValueError("duplicate datetime-symbol-signal_name rows are not allowed")
    if (cleaned["available_at"] > cleaned["datetime"]).any():
        raise ValueError("available_at must be less than or equal to datetime")
    return cleaned


def _validate_v01_signal_columns(signal_frame: pd.DataFrame) -> None:
    if signal_frame["signal_binary"].isna().any():
        raise ValueError("signal_binary is required")
    if not signal_frame["signal_binary"].isin([0, 1]).all():
        raise ValueError("signal_binary must be binary: 0 or 1")


def _validate_v02_signal_columns(signal_frame: pd.DataFrame) -> None:
    if signal_frame["score"].isna().any():
        raise ValueError("score is required")
    if signal_frame["direction"].isna().any():
        raise ValueError("direction is required")
    if signal_frame["target_weight"].isna().any():
        raise ValueError("target_weight is required")
    if not signal_frame["direction"].isin([-1, 0, 1]).all():
        raise ValueError("direction must be ternary: -1, 0, or 1")
    if (signal_frame["target_weight"] < -1.0).any() or (signal_frame["target_weight"] > 1.0).any():
        raise ValueError("target_weight must be within [-1.0, 1.0]")


def _select_signal_name(signal_frame: pd.DataFrame, signal_name: str | None) -> tuple[pd.DataFrame, str | None]:
    unique_signal_names = _unique_non_null_values(signal_frame["signal_name"])
    if signal_name is not None:
        filtered = signal_frame.loc[signal_frame["signal_name"].astype(str) == signal_name].copy().reset_index(drop=True)
        if filtered.empty:
            raise ValueError(f"signal.csv does not contain requested signal_name {signal_name!r}")
        return filtered, signal_name
    if len(unique_signal_names) > 1:
        names = ", ".join(sorted(unique_signal_names))
        raise ValueError(f"signal.csv contains multiple signal_name values: {names}. Specify signal_name explicitly")
    if len(unique_signal_names) == 1:
        selected_signal_name = unique_signal_names[0]
        return signal_frame.loc[signal_frame["signal_name"].astype(str) == selected_signal_name].copy().reset_index(drop=True), selected_signal_name
    return signal_frame.copy().reset_index(drop=True), None


def _resolve_target_symbol(signal_frame: pd.DataFrame, market_data: pd.DataFrame, symbol: str | None) -> str:
    market_symbol = (
        _optional_single_unique_value(
            market_data["symbol"],
            "market_data symbol",
            multiple_message="market_data must contain exactly one symbol for custom_signal",
        )
        if "symbol" in market_data.columns
        else None
    )
    signal_symbol = _require_single_unique_value(
        signal_frame["symbol"],
        "symbol",
        missing_message="symbol is required",
        multiple_message="signal.csv must contain exactly one symbol for custom_signal",
    )

    if symbol is not None:
        if signal_symbol != symbol:
            raise ValueError(f"signal.csv symbol {signal_symbol!r} does not match requested symbol {symbol!r}")
        if market_symbol is not None and market_symbol != symbol:
            raise ValueError(f"market_data symbol {market_symbol!r} does not match requested symbol {symbol!r}")
        return symbol
    if market_symbol is not None:
        if market_symbol != signal_symbol:
            raise ValueError(f"market_data symbol {market_symbol!r} does not match signal.csv symbol {signal_symbol!r}")
        return market_symbol
    return signal_symbol


def _filter_and_validate_symbol(signal_frame: pd.DataFrame, target_symbol: str) -> pd.DataFrame:
    filtered = signal_frame.loc[signal_frame["symbol"].astype(str) == str(target_symbol)].copy().reset_index(drop=True)
    if filtered.empty:
        raise ValueError(f"No signal rows found for symbol {target_symbol!r}")
    return filtered


def _extract_market_datetimes(market_data: pd.DataFrame) -> pd.Index:
    if "datetime" not in market_data.columns:
        raise ValueError("market_data requires a datetime column")
    market_datetimes = _normalize_daily_datetimes(market_data["datetime"])
    if market_datetimes.isna().any():
        raise ValueError("market_data datetime column contains missing values")
    if market_datetimes.duplicated().any():
        raise ValueError("market_data datetime values must be unique")
    return pd.Index(market_datetimes)


def _normalize_daily_datetimes(values: pd.Series) -> pd.Series:
    return values.map(_normalize_daily_datetime)


def _normalize_daily_datetime(value: object) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    try:
        parsed = pd.to_datetime(value, errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Could not parse datetime value {value!r}") from exc
    return pd.Timestamp(parsed.date())


def _validate_market_alignment(signal_frame: pd.DataFrame, market_datetimes: pd.Index) -> None:
    signal_datetimes = pd.Index(signal_frame["datetime"])
    extra = signal_datetimes.difference(market_datetimes)
    if len(extra):
        raise ValueError("signal dates must align with market data dates")


def _require_single_unique_value(
    series: pd.Series,
    field_name: str,
    *,
    missing_message: str | None = None,
    multiple_message: str | None = None,
) -> str:
    unique_values = _unique_non_null_values(series)
    if len(unique_values) == 1:
        return unique_values[0]
    if len(unique_values) == 0:
        raise ValueError(missing_message or f"{field_name} is required")
    raise ValueError(multiple_message or f"{field_name} must contain exactly one value")


def _optional_single_unique_value(
    series: pd.Series,
    field_name: str,
    *,
    multiple_message: str | None = None,
    on_multiple: str = "raise",
) -> str | None:
    unique_values = _unique_non_null_values(series)
    if len(unique_values) == 1:
        return unique_values[0]
    if len(unique_values) == 0:
        return None
    if on_multiple == "omit":
        return None
    raise ValueError(multiple_message or f"{field_name} must contain exactly one value")


def _unique_non_null_values(series: pd.Series) -> list[str]:
    non_null = series.dropna().astype(str)
    unique_values = pd.Index(non_null.unique())
    return [str(value) for value in unique_values]
