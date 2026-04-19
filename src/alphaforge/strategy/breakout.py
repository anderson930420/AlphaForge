from __future__ import annotations

from typing import Any

import pandas as pd

from alphaforge.schemas import StrategySpec
from alphaforge.strategy.base import Strategy


def validate_candidate_parameters(parameters: dict[str, Any]) -> None:
    lookback_window = int(parameters["lookback_window"])
    if lookback_window <= 0:
        raise ValueError("lookback_window must be a positive integer")


class BreakoutStrategy(Strategy):
    """Long-flat breakout strategy driven by a rolling prior-bar high."""

    def __init__(self, spec: StrategySpec) -> None:
        super().__init__(spec)
        validate_candidate_parameters(spec.parameters)

    def generate_signals(self, market_data: pd.DataFrame) -> pd.Series:
        close = market_data["close"].astype(float)
        lookback_window = int(self.spec.parameters["lookback_window"])
        prior_high = close.shift(1).rolling(window=lookback_window, min_periods=lookback_window).max()
        signals = (close > prior_high).astype(float).fillna(0.0)
        signals.name = "target_position"
        return signals
