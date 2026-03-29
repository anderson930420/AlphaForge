from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from alphaforge.schemas import StrategySpec


class Strategy(ABC):
    """Common interface for all AlphaForge strategies."""

    def __init__(self, spec: StrategySpec) -> None:
        self.spec = spec

    @abstractmethod
    def generate_signals(self, market_data: pd.DataFrame) -> pd.Series:
        """Return target position weights indexed like market_data."""
