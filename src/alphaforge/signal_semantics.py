"""Shared signal, target-position, and execution-action semantics.

This module defines the vocabulary AlphaForge expects from external signal
producers such as SignalForge. It does not download data, optimize signals, or
change the current backtest engine. The existing ``custom_signal`` path can keep
using its v0.1 long/flat file contract while newer adapters converge on these
v0.2 semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum


DEFAULT_SIGN_TOLERANCE = 1e-12


class Direction(IntEnum):
    """Expected alpha direction before portfolio sizing."""

    BEARISH = -1
    NEUTRAL = 0
    BULLISH = 1


class PositionSide(IntEnum):
    """Signed target exposure side."""

    SHORT = -1
    FLAT = 0
    LONG = 1


class OrderSide(StrEnum):
    """Order-side vocabulary derived from current and target exposure."""

    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"


class PositionEffect(StrEnum):
    """Position transition derived from current and target exposure."""

    OPEN_LONG = "OPEN_LONG"
    INCREASE_LONG = "INCREASE_LONG"
    REDUCE_LONG = "REDUCE_LONG"
    CLOSE_LONG = "CLOSE_LONG"
    OPEN_SHORT = "OPEN_SHORT"
    INCREASE_SHORT = "INCREASE_SHORT"
    REDUCE_SHORT = "REDUCE_SHORT"
    CLOSE_SHORT = "CLOSE_SHORT"
    REVERSE_LONG_TO_SHORT = "REVERSE_LONG_TO_SHORT"
    REVERSE_SHORT_TO_LONG = "REVERSE_SHORT_TO_LONG"
    NO_ACTION = "NO_ACTION"


@dataclass(frozen=True)
class ExecutionAction:
    """Resolved execution action for a target-weight transition."""

    current_weight: float
    target_weight: float
    delta_weight: float
    current_side: PositionSide
    target_side: PositionSide
    order_side: OrderSide
    position_effect: PositionEffect


def direction_from_score(
    score: float,
    *,
    long_threshold: float,
    short_threshold: float | None = None,
) -> Direction:
    """Map a continuous alpha score to bullish/neutral/bearish direction.

    ``short_threshold`` defaults to ``-long_threshold`` so symmetric policies
    can specify only one positive threshold. Threshold equality is neutral by
    design; a score must clear the threshold to express a directional edge.
    """
    resolved_short_threshold = -long_threshold if short_threshold is None else short_threshold
    if resolved_short_threshold >= long_threshold:
        raise ValueError("short_threshold must be less than long_threshold")

    numeric_score = float(score)
    if numeric_score > long_threshold:
        return Direction.BULLISH
    if numeric_score < resolved_short_threshold:
        return Direction.BEARISH
    return Direction.NEUTRAL


def target_side_from_weight(weight: float, *, tolerance: float = DEFAULT_SIGN_TOLERANCE) -> PositionSide:
    """Classify a target weight as long, flat, or short."""
    numeric_weight = float(weight)
    if numeric_weight > tolerance:
        return PositionSide.LONG
    if numeric_weight < -tolerance:
        return PositionSide.SHORT
    return PositionSide.FLAT


def direction_to_target_weight(
    direction: Direction | int,
    *,
    long_weight: float = 1.0,
    short_weight: float = -1.0,
) -> float:
    """Convert a direction into a fixed signed target weight."""
    if long_weight <= 0:
        raise ValueError("long_weight must be positive")
    if short_weight >= 0:
        raise ValueError("short_weight must be negative")

    resolved_direction = Direction(int(direction))
    if resolved_direction is Direction.BULLISH:
        return float(long_weight)
    if resolved_direction is Direction.BEARISH:
        return float(short_weight)
    return 0.0


def resolve_execution_action(
    current_weight: float,
    target_weight: float,
    *,
    tolerance: float = DEFAULT_SIGN_TOLERANCE,
) -> ExecutionAction:
    """Resolve Buy/Sell/Close/Hold semantics from current and target weights.

    Strategies should not emit Buy, Sell, or Close labels directly. They should
    emit target exposure. This resolver derives the executable intent from the
    current exposure and target exposure.
    """
    current = float(current_weight)
    target = float(target_weight)
    delta = target - current
    current_side = target_side_from_weight(current, tolerance=tolerance)
    target_side = target_side_from_weight(target, tolerance=tolerance)

    if delta > tolerance:
        order_side = OrderSide.BUY
    elif delta < -tolerance:
        order_side = OrderSide.SELL
    else:
        order_side = OrderSide.NONE

    position_effect = _resolve_position_effect(current, target, current_side, target_side, tolerance=tolerance)
    return ExecutionAction(
        current_weight=current,
        target_weight=target,
        delta_weight=delta,
        current_side=current_side,
        target_side=target_side,
        order_side=order_side,
        position_effect=position_effect,
    )


def _resolve_position_effect(
    current_weight: float,
    target_weight: float,
    current_side: PositionSide,
    target_side: PositionSide,
    *,
    tolerance: float,
) -> PositionEffect:
    if abs(target_weight - current_weight) <= tolerance:
        return PositionEffect.NO_ACTION

    if current_side is PositionSide.FLAT and target_side is PositionSide.LONG:
        return PositionEffect.OPEN_LONG
    if current_side is PositionSide.FLAT and target_side is PositionSide.SHORT:
        return PositionEffect.OPEN_SHORT
    if current_side is PositionSide.LONG and target_side is PositionSide.FLAT:
        return PositionEffect.CLOSE_LONG
    if current_side is PositionSide.SHORT and target_side is PositionSide.FLAT:
        return PositionEffect.CLOSE_SHORT
    if current_side is PositionSide.LONG and target_side is PositionSide.SHORT:
        return PositionEffect.REVERSE_LONG_TO_SHORT
    if current_side is PositionSide.SHORT and target_side is PositionSide.LONG:
        return PositionEffect.REVERSE_SHORT_TO_LONG

    if current_side is PositionSide.LONG and target_side is PositionSide.LONG:
        if target_weight > current_weight:
            return PositionEffect.INCREASE_LONG
        return PositionEffect.REDUCE_LONG

    if current_side is PositionSide.SHORT and target_side is PositionSide.SHORT:
        if target_weight < current_weight:
            return PositionEffect.INCREASE_SHORT
        return PositionEffect.REDUCE_SHORT

    return PositionEffect.NO_ACTION
