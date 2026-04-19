from __future__ import annotations

from typing import Any

import pandas as pd

from alphaforge.schemas import StrategySpec
from alphaforge.strategy.base import Strategy


def validate_candidate_parameters(parameters: dict[str, Any]) -> None:
    short_window = int(parameters["short_window"])
    long_window = int(parameters["long_window"])
    if short_window <= 0 or long_window <= 0:
        raise ValueError("Window lengths must be positive integers")
    if short_window >= long_window:
        raise ValueError("short_window must be smaller than long_window")


class MovingAverageCrossoverStrategy(Strategy):
    """Canonical MVP moving-average crossover strategy.

    This strategy emits long-flat target positions only: ``1.0`` when the
    short moving average is above the long moving average, otherwise ``0.0``.
    The emitted values target the next tradable interval rather than the
    current bar.
    """

    def __init__(self, spec: StrategySpec) -> None:
        super().__init__(spec)
        validate_candidate_parameters(spec.parameters)

    def generate_signals(self, market_data: pd.DataFrame) -> pd.Series:
        """Return next-bar long-flat targets from the close-price crossover."""
        close = market_data["close"].astype(float)
        short_window = int(self.spec.parameters["short_window"])
        long_window = int(self.spec.parameters["long_window"])
        short_ma = close.rolling(window=short_window, min_periods=short_window).mean()
        long_ma = close.rolling(window=long_window, min_periods=long_window).mean()
        signals = (short_ma > long_ma).astype(float).fillna(0.0)
        signals.name = "target_position"
        return signals
