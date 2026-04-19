from __future__ import annotations

"""Literal defaults and input-policy constants for AlphaForge.

This module is intentionally constants-only. It provides shared defaults,
ranges, and alias maps that canonical owners consume, but it does not validate
market data, define execution semantics, or own artifact schemas.
"""

from pathlib import Path

INITIAL_CAPITAL = 100_000.0
DEFAULT_FEE_RATE = 0.001
DEFAULT_SLIPPAGE_RATE = 0.0005
DEFAULT_RANDOM_SEED = 7
DEFAULT_ANNUALIZATION = 252

SHORT_WINDOW_RANGE = [5, 10, 20]
LONG_WINDOW_RANGE = [50, 100, 150]

REQUIRED_COLUMNS = ("datetime", "open", "high", "low", "close", "volume")
CSV_COLUMN_ALIASES = {
    "date": "datetime",
    "timestamp": "datetime",
}
MISSING_DATA_POLICY = (
    "Drop rows with missing datetime or close values, forward-fill open/high/low/close,"
    " and fill missing volume with 0 after sorting."
)

ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "outputs"
