from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.schemas import StrategySpec
from alphaforge.strategy.ma_crossover import MovingAverageCrossoverStrategy


def test_ma_crossover_generates_long_flat_signals() -> None:
    market_data = pd.DataFrame({"close": [1, 2, 3, 2, 1, 2, 3, 4]})
    strategy = MovingAverageCrossoverStrategy(
        StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 3})
    )

    signals = strategy.generate_signals(market_data)

    assert signals.tolist() == [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 1.0]


def test_ma_crossover_rejects_invalid_windows() -> None:
    with pytest.raises(ValueError, match="short_window"):
        MovingAverageCrossoverStrategy(
            StrategySpec(name="ma_crossover", parameters={"short_window": 5, "long_window": 5})
        )
