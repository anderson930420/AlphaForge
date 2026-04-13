from __future__ import annotations

from pathlib import Path

INITIAL_CAPITAL = 100_000.0
DEFAULT_FEE_RATE = 0.001
DEFAULT_SLIPPAGE_RATE = 0.0005
DEFAULT_RANDOM_SEED = 7
DEFAULT_ANNUALIZATION = 252

SHORT_WINDOW_RANGE = [5, 10, 20]
LONG_WINDOW_RANGE = [50, 100, 150]

ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "outputs"
