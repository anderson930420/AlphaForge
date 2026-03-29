from __future__ import annotations

import pandas as pd

from alphaforge.schemas import StrategySpec
from alphaforge.strategy.base import Strategy


class MovingAverageCrossoverStrategy(Strategy):
    """Long-flat moving average crossover baseline."""

    def __init__(self, spec: StrategySpec) -> None:
        super().__init__(spec)
        short_window = int(spec.parameters["short_window"])
        long_window = int(spec.parameters["long_window"])
        if short_window <= 0 or long_window <= 0:
            raise ValueError("Window lengths must be positive integers")
        if short_window >= long_window:
            raise ValueError("short_window must be smaller than long_window")

    def generate_signals(self, market_data: pd.DataFrame) -> pd.Series:
        close = market_data["close"].astype(float)
        short_window = int(self.spec.parameters["short_window"])
        long_window = int(self.spec.parameters["long_window"])
        short_ma = close.rolling(window=short_window, min_periods=short_window).mean()
        long_ma = close.rolling(window=long_window, min_periods=long_window).mean()
        signals = (short_ma > long_ma).astype(float).fillna(0.0)
        signals.name = "target_position"
        return signals
