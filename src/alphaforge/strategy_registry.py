from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

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
)
_REGISTRATION_BY_NAME = {registration.name: registration for registration in _REGISTRATIONS}


def supported_strategy_families() -> tuple[str, ...]:
    return tuple(registration.name for registration in _REGISTRATIONS)


def get_strategy_registration(strategy_name: str) -> StrategyFamilyRegistration:
    registration = _REGISTRATION_BY_NAME.get(strategy_name)
    if registration is None:
        supported = ", ".join(supported_strategy_families())
        raise ValueError(f"Unsupported strategy: {strategy_name}. Supported strategies: {supported}")
    return registration


def build_strategy_from_registry(strategy_spec: StrategySpec) -> Strategy:
    registration = get_strategy_registration(strategy_spec.name)
    return registration.builder(strategy_spec)
