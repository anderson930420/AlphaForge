from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .policy_types import ParameterGrid
from .schemas import StrategySpec
from .strategy.base import Strategy
from .strategy.breakout import BreakoutStrategy
from .strategy.ma_crossover import MovingAverageCrossoverStrategy


@dataclass(frozen=True)
class StrategyFamilyRegistration:
    name: str
    parameter_names: tuple[str, ...]
    integer_window_parameters: tuple[str, ...]
    builder: Callable[[StrategySpec], Strategy]
    validation_only: bool = False


def _raise_validation_only_strategy(strategy_spec: StrategySpec) -> Strategy:
    raise ValueError(
        f"{strategy_spec.name} is validation-only and requires the custom-signal signal-file workflow path"
    )


_REGISTRATIONS: tuple[StrategyFamilyRegistration, ...] = (
    StrategyFamilyRegistration(
        name="ma_crossover",
        parameter_names=("short_window", "long_window"),
        integer_window_parameters=("long_window",),
        builder=MovingAverageCrossoverStrategy,
    ),
    StrategyFamilyRegistration(
        name="breakout",
        parameter_names=("lookback_window",),
        integer_window_parameters=("lookback_window",),
        builder=BreakoutStrategy,
    ),
    StrategyFamilyRegistration(
        name="custom_signal",
        parameter_names=(),
        integer_window_parameters=(),
        builder=_raise_validation_only_strategy,
        validation_only=True,
    ),
)
_REGISTRATION_BY_NAME = {registration.name: registration for registration in _REGISTRATIONS}


def supported_strategy_families() -> tuple[str, ...]:
    return tuple(registration.name for registration in _REGISTRATIONS if not registration.validation_only)


def get_strategy_registration(strategy_name: str) -> StrategyFamilyRegistration:
    registration = _REGISTRATION_BY_NAME.get(strategy_name)
    if registration is None:
        supported = ", ".join(supported_strategy_families())
        raise ValueError(f"Unsupported strategy: {strategy_name}. Supported strategies: {supported}")
    return registration


def build_strategy_from_registry(strategy_spec: StrategySpec) -> Strategy:
    registration = get_strategy_registration(strategy_spec.name)
    if registration.validation_only:
        raise ValueError(
            f"{strategy_spec.name} is validation-only and requires the custom-signal signal-file workflow path"
        )
    return registration.builder(strategy_spec)


def validate_parameter_grid_for_strategy(strategy_name: str, parameter_grid: ParameterGrid) -> None:
    registration = get_strategy_registration(strategy_name)
    if registration.validation_only:
        if parameter_grid:
            names = ", ".join(sorted(parameter_grid))
            raise ValueError(f"{strategy_name} is validation-only and accepts no parameter grid parameters: {names}")
        return
    expected = set(registration.parameter_names)
    provided = set(parameter_grid)
    missing = sorted(expected - provided)
    unexpected = sorted(provided - expected)
    if missing:
        names = ", ".join(missing)
        raise ValueError(f"{strategy_name} parameter grid is missing required parameters: {names}")
    if unexpected:
        names = ", ".join(unexpected)
        raise ValueError(f"{strategy_name} parameter grid contains unexpected parameters: {names}")
