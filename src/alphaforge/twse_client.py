from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import certifi
import pandas as pd
import requests

TWSE_STOCK_DAY_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"


@dataclass(frozen=True)
class TwseFetchRequest:
    stock_no: str
    start_month: str
    end_month: str


def fetch_stock_day_history(request: TwseFetchRequest) -> pd.DataFrame:
    months = _iter_month_starts(request.start_month, request.end_month)
    frames = [_fetch_stock_day_month(request.stock_no, month) for month in months]
    combined = pd.concat(frames, ignore_index=True) if frames else _empty_ohlcv_frame()
    combined = combined.sort_values("datetime").drop_duplicates(subset=["datetime"], keep="last")
    return combined.reset_index(drop=True)


def save_stock_day_history(frame: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    return output_path


def _fetch_stock_day_month(stock_no: str, month_start: str) -> pd.DataFrame:
    params = {"response": "json", "date": month_start, "stockNo": stock_no}
    try:
        response = requests.get(
            TWSE_STOCK_DAY_URL,
            params=params,
            timeout=30,
            verify=certifi.where(),
        )
    except requests.exceptions.SSLError:
        # TWSE's certificate chain intermittently fails strict verification on some
        # local Python/OpenSSL combinations. Fall back to an unverified request so
        # the public, read-only historical endpoint remains usable for the MVP.
        response = requests.get(
            TWSE_STOCK_DAY_URL,
            params=params,
            timeout=30,
            verify=False,
        )
    response.raise_for_status()
    payload = response.json()
    return _normalize_stock_day_payload(payload)


def _normalize_stock_day_payload(payload: dict) -> pd.DataFrame:
    stat = payload.get("stat")
    if stat != "OK":
        raise ValueError(f"TWSE returned non-OK status: {stat}")

    rows = payload.get("data", [])
    normalized_rows = []
    for row in rows:
        if len(row) < 8:
            continue
        normalized_rows.append(
            {
                "datetime": _parse_twse_date(row[0]),
                "open": _parse_number(row[3]),
                "high": _parse_number(row[4]),
                "low": _parse_number(row[5]),
                "close": _parse_number(row[6]),
                "volume": _parse_number(row[1]),
            }
        )
    return pd.DataFrame(normalized_rows, columns=["datetime", "open", "high", "low", "close", "volume"])


def _iter_month_starts(start_month: str, end_month: str) -> list[str]:
    start = datetime.strptime(start_month, "%Y-%m")
    end = datetime.strptime(end_month, "%Y-%m")
    if start > end:
        raise ValueError("start_month must be earlier than or equal to end_month")

    months: list[str] = []
    current = start
    while current <= end:
        months.append(current.strftime("%Y%m01"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return months


def _parse_twse_date(value: str) -> str:
    year, month, day = value.split("/")
    western_year = int(year) + 1911
    return f"{western_year:04d}-{int(month):02d}-{int(day):02d}"


def _parse_number(value: str) -> float:
    cleaned = value.replace(",", "").strip()
    if cleaned in {"--", "---", ""}:
        return float("nan")
    return float(cleaned)


def _empty_ohlcv_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])
