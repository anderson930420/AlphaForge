from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from alphaforge.schemas import StrategySpec


class Strategy(ABC):
    """Common runtime interface for AlphaForge strategies.

    Strategy implementations consume validated single-asset OHLCV market data
    and emit target positions indexed like the input frame. In the current MVP,
    those targets are long-flat only and are interpreted by backtest.py as the
    desired position for the next tradable interval.
    """

    def __init__(self, spec: StrategySpec) -> None:
        self.spec = spec

    @abstractmethod
    def generate_signals(self, market_data: pd.DataFrame) -> pd.Series:
        """Return next-bar target positions aligned to ``market_data``."""
