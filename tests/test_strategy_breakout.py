from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.schemas import StrategySpec
from alphaforge.strategy.breakout import BreakoutStrategy


def test_breakout_generates_long_flat_signals() -> None:
    market_data = pd.DataFrame({"close": [1, 2, 3, 2, 4, 5]})
    strategy = BreakoutStrategy(StrategySpec(name="breakout", parameters={"lookback_window": 2}))

    signals = strategy.generate_signals(market_data)

    assert signals.tolist() == [0.0, 0.0, 1.0, 0.0, 1.0, 1.0]


def test_breakout_rejects_invalid_lookback_window() -> None:
    with pytest.raises(ValueError, match="lookback_window"):
        BreakoutStrategy(StrategySpec(name="breakout", parameters={"lookback_window": 0}))
