from __future__ import annotations

from itertools import product
from typing import Any

from .schemas import StrategySpec


def grid_search_parameters(parameter_grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    if not parameter_grid:
        return [{}]
    keys = list(parameter_grid)
    return [dict(zip(keys, values, strict=True)) for values in product(*(parameter_grid[key] for key in keys))]


def build_strategy_specs(strategy_name: str, parameter_grid: dict[str, list[Any]]) -> list[StrategySpec]:
    specs: list[StrategySpec] = []
    attempted = grid_search_parameters(parameter_grid)
    for params in attempted:
        short_window = params.get("short_window")
        long_window = params.get("long_window")
        if short_window is not None and long_window is not None and int(short_window) >= int(long_window):
            continue
        specs.append(StrategySpec(name=strategy_name, parameters=params))
    if attempted and not specs:
        raise ValueError("No valid parameter combinations remain after strategy validation")
    return specs
