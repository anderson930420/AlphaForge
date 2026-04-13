from __future__ import annotations

from itertools import product
from typing import Any

from .schemas import StrategySpec
from .strategy.ma_crossover import validate_candidate_parameters as validate_ma_crossover_candidate_parameters


def grid_search_parameters(parameter_grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    if not parameter_grid:
        return [{}]
    keys = list(parameter_grid)
    return [dict(zip(keys, values, strict=True)) for values in product(*(parameter_grid[key] for key in keys))]


def build_strategy_specs(strategy_name: str, parameter_grid: dict[str, list[Any]]) -> list[StrategySpec]:
    specs: list[StrategySpec] = []
    attempted = grid_search_parameters(parameter_grid)
    for params in attempted:
        if not _validate_strategy_candidate(strategy_name, params):
            continue
        specs.append(StrategySpec(name=strategy_name, parameters=params))
    if attempted and not specs:
        raise ValueError("No valid parameter combinations remain after strategy validation")
    return specs


def _validate_strategy_candidate(strategy_name: str, parameters: dict[str, Any]) -> bool:
    if strategy_name == "ma_crossover":
        try:
            validate_ma_crossover_candidate_parameters(parameters)
        except ValueError:
            return False
    return True
