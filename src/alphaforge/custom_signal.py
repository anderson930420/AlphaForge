from __future__ import annotations

"""External signal-file validation for the custom-signal workflow.

This module owns the file contract for precomputed signal inputs. It does not
compute signals, import external strategy internals, or change execution
semantics.
"""

from pathlib import Path

import pandas as pd


REQUIRED_SIGNAL_COLUMNS = (
    "datetime",
    "available_at",
    "symbol",
    "signal_name",
    "signal_value",
    "signal_binary",
    "source",
)


def load_custom_signal_positions(
    signal_file: Path | str,
    market_data: pd.DataFrame,
    symbol: str | None = None,
) -> tuple[pd.Series, dict[str, object]]:
    signal_frame = _load_signal_frame(signal_file)
    signal_frame = _coerce_signal_frame(signal_frame)
    target_symbol = _resolve_target_symbol(signal_frame, market_data, symbol)
    signal_frame = _filter_and_validate_symbol(signal_frame, target_symbol)
    market_datetimes = _extract_market_datetimes(market_data)
    _validate_market_alignment(signal_frame, market_datetimes)

    signal_binary_by_datetime = signal_frame.set_index("datetime")["signal_binary"].astype(float)
    target_position = market_datetimes.map(signal_binary_by_datetime).astype(float)
    target_position = pd.Series(target_position.to_numpy(dtype=float), index=market_data.index, name="target_position")

    metadata: dict[str, object] = {"symbol": target_symbol, "signal_row_count": int(len(signal_frame))}
    signal_name = _single_unique_value(signal_frame["signal_name"])
    if signal_name is not None:
        metadata["signal_name"] = signal_name
    source = _single_unique_value(signal_frame["source"])
    if source is not None:
        metadata["source"] = source
    return target_position, metadata


def _load_signal_frame(signal_file: Path | str) -> pd.DataFrame:
    signal_path = Path(signal_file)
    frame = pd.read_csv(signal_path)
    renamed = frame.rename(columns={name: name.strip().lower() for name in frame.columns})
    missing = [column for column in REQUIRED_SIGNAL_COLUMNS if column not in renamed.columns]
    if missing:
        raise ValueError(f"Missing required signal columns: {missing}")
    return renamed[list(REQUIRED_SIGNAL_COLUMNS)].copy()


def _coerce_signal_frame(signal_frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = signal_frame.copy()
    cleaned["datetime"] = pd.to_datetime(cleaned["datetime"], utc=False, errors="raise")
    cleaned["available_at"] = pd.to_datetime(cleaned["available_at"], utc=False, errors="raise")
    cleaned["signal_binary"] = pd.to_numeric(cleaned["signal_binary"], errors="raise")

    if cleaned["datetime"].isna().any():
        raise ValueError("datetime is required")
    if cleaned["available_at"].isna().any():
        raise ValueError("available_at is required")
    if cleaned["symbol"].isna().any():
        raise ValueError("symbol is required")
    if cleaned["signal_binary"].isna().any():
        raise ValueError("signal_binary is required")
    if cleaned["datetime"].duplicated().any():
        raise ValueError("duplicate datetime for the same symbol fails")
    if (cleaned["available_at"] > cleaned["datetime"]).any():
        raise ValueError("available_at must be less than or equal to datetime")
    if not cleaned["signal_binary"].isin([0, 1]).all():
        raise ValueError("signal_binary must be binary: 0 or 1")
    return cleaned


def _resolve_target_symbol(signal_frame: pd.DataFrame, market_data: pd.DataFrame, symbol: str | None) -> str:
    market_symbol = _single_unique_value(market_data["symbol"]) if "symbol" in market_data.columns else None
    signal_symbol = _single_unique_value(signal_frame["symbol"])
    if signal_symbol is None:
        raise ValueError("custom-signal validation requires a single symbol in signal.csv")

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
    market_datetimes = pd.to_datetime(market_data["datetime"], utc=False, errors="raise")
    if market_datetimes.isna().any():
        raise ValueError("market_data datetime column contains missing values")
    if market_datetimes.duplicated().any():
        raise ValueError("market_data datetime values must be unique")
    if "symbol" in market_data.columns and _single_unique_value(market_data["symbol"]) is None:
        raise ValueError("market_data must contain a single symbol for custom-signal validation")
    return pd.Index(market_datetimes)


def _validate_market_alignment(signal_frame: pd.DataFrame, market_datetimes: pd.Index) -> None:
    signal_datetimes = pd.Index(signal_frame["datetime"])
    missing = market_datetimes.difference(signal_datetimes)
    extra = signal_datetimes.difference(market_datetimes)
    if len(missing) or len(extra):
        raise ValueError("signal dates must align with market data dates")


def _single_unique_value(series: pd.Series) -> str | None:
    non_null = series.dropna().astype(str)
    unique_values = pd.Index(non_null.unique())
    if len(unique_values) == 1:
        return str(unique_values[0])
    if len(unique_values) == 0:
        return None
    return None
