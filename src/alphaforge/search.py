from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any

from .policy_types import ParameterGrid
from .schemas import StrategySpec
from .strategy.breakout import validate_candidate_parameters as validate_breakout_candidate_parameters
from .strategy.ma_crossover import validate_candidate_parameters as validate_ma_crossover_candidate_parameters

SUPPORTED_STRATEGY_FAMILIES = ("ma_crossover", "breakout")
MA_CROSSOVER_SEARCH_PARAMETER_NAMES = ("short_window", "long_window")
BREAKOUT_SEARCH_PARAMETER_NAMES = ("lookback_window",)
SEARCH_PARAMETER_NAMES_BY_STRATEGY = {
    "ma_crossover": MA_CROSSOVER_SEARCH_PARAMETER_NAMES,
    "breakout": BREAKOUT_SEARCH_PARAMETER_NAMES,
}


@dataclass(frozen=True)
class SearchSpaceEvaluation:
    strategy_name: str
    parameter_names: tuple[str, ...]
    strategy_specs: tuple[StrategySpec, ...]
    invalid_combinations: tuple[dict[str, Any], ...]
    attempted_combination_count: int

    @property
    def valid_combination_count(self) -> int:
        return len(self.strategy_specs)

    @property
    def invalid_combination_count(self) -> int:
        return len(self.invalid_combinations)


def grid_search_parameters(parameter_grid: ParameterGrid) -> list[dict[str, Any]]:
    if not parameter_grid:
        return [{}]
    keys = list(parameter_grid)
    return [dict(zip(keys, values, strict=True)) for values in product(*(parameter_grid[key] for key in keys))]


def evaluate_strategy_search_space(strategy_name: str, parameter_grid: ParameterGrid) -> SearchSpaceEvaluation:
    parameter_names = tuple(parameter_grid)
    attempted = grid_search_parameters(parameter_grid)
    strategy_specs: list[StrategySpec] = []
    invalid_combinations: list[dict[str, Any]] = []

    _validate_search_parameter_grid(strategy_name, parameter_grid)
    for params in attempted:
        if not _validate_strategy_candidate(strategy_name, params):
            invalid_combinations.append(dict(params))
            continue
        strategy_specs.append(StrategySpec(name=strategy_name, parameters=params))
    if attempted and not strategy_specs:
        raise ValueError("No valid parameter combinations remain after strategy validation")
    return SearchSpaceEvaluation(
        strategy_name=strategy_name,
        parameter_names=parameter_names,
        strategy_specs=tuple(strategy_specs),
        invalid_combinations=tuple(invalid_combinations),
        attempted_combination_count=len(attempted),
    )


def build_strategy_specs(strategy_name: str, parameter_grid: ParameterGrid) -> list[StrategySpec]:
    evaluation = evaluate_strategy_search_space(strategy_name, parameter_grid)
    return list(evaluation.strategy_specs)


def _validate_search_parameter_grid(strategy_name: str, parameter_grid: ParameterGrid) -> None:
    expected_names = SEARCH_PARAMETER_NAMES_BY_STRATEGY.get(strategy_name)
    if expected_names is None:
        raise ValueError(f"Unsupported strategy: {strategy_name}")
    expected = set(expected_names)
    provided = set(parameter_grid)
    missing = sorted(expected - provided)
    unexpected = sorted(provided - expected)
    family_label = "MA crossover" if strategy_name == "ma_crossover" else "breakout"
    if missing:
        raise ValueError(f"{family_label} search requires parameter grids for: {', '.join(missing)}")
    if unexpected:
        raise ValueError(f"{family_label} search does not accept parameters: {', '.join(unexpected)}")


def _validate_strategy_candidate(strategy_name: str, parameters: dict[str, Any]) -> bool:
    validator = {
        "ma_crossover": validate_ma_crossover_candidate_parameters,
        "breakout": validate_breakout_candidate_parameters,
    }.get(strategy_name)
    if validator is None:
        raise ValueError(f"Unsupported strategy: {strategy_name}")
    try:
        validator(parameters)
    except ValueError:
        return False
    return True
