from __future__ import annotations

import pytest

from alphaforge.signal_semantics import (
    Direction,
    OrderSide,
    PositionEffect,
    PositionSide,
    direction_from_score,
    direction_to_target_weight,
    resolve_execution_action,
    target_side_from_weight,
)


@pytest.mark.parametrize(
    "score, expected_direction",
    [
        (0.011, Direction.BULLISH),
        (0.010, Direction.NEUTRAL),
        (0.000, Direction.NEUTRAL),
        (-0.010, Direction.NEUTRAL),
        (-0.011, Direction.BEARISH),
    ],
)
def test_direction_from_score_uses_strict_symmetric_thresholds(score: float, expected_direction: Direction) -> None:
    assert direction_from_score(score, long_threshold=0.01) is expected_direction


def test_direction_from_score_accepts_asymmetric_thresholds() -> None:
    assert direction_from_score(0.021, long_threshold=0.02, short_threshold=-0.01) is Direction.BULLISH
    assert direction_from_score(-0.011, long_threshold=0.02, short_threshold=-0.01) is Direction.BEARISH
    assert direction_from_score(0.015, long_threshold=0.02, short_threshold=-0.01) is Direction.NEUTRAL


def test_direction_from_score_rejects_overlapping_thresholds() -> None:
    with pytest.raises(ValueError, match="short_threshold must be less than long_threshold"):
        direction_from_score(0.0, long_threshold=0.01, short_threshold=0.01)


@pytest.mark.parametrize(
    "weight, expected_side",
    [
        (0.05, PositionSide.LONG),
        (0.0, PositionSide.FLAT),
        (1e-13, PositionSide.FLAT),
        (-1e-13, PositionSide.FLAT),
        (-0.05, PositionSide.SHORT),
    ],
)
def test_target_side_from_weight_classifies_signed_exposure(weight: float, expected_side: PositionSide) -> None:
    assert target_side_from_weight(weight) is expected_side


@pytest.mark.parametrize(
    "direction, expected_weight",
    [
        (Direction.BULLISH, 0.25),
        (Direction.NEUTRAL, 0.0),
        (Direction.BEARISH, -0.15),
        (1, 0.25),
        (0, 0.0),
        (-1, -0.15),
    ],
)
def test_direction_to_target_weight_uses_signed_weights(direction: Direction | int, expected_weight: float) -> None:
    assert direction_to_target_weight(direction, long_weight=0.25, short_weight=-0.15) == expected_weight


def test_direction_to_target_weight_rejects_invalid_weight_signs() -> None:
    with pytest.raises(ValueError, match="long_weight must be positive"):
        direction_to_target_weight(Direction.BULLISH, long_weight=0.0)
    with pytest.raises(ValueError, match="short_weight must be negative"):
        direction_to_target_weight(Direction.BEARISH, short_weight=0.0)


@pytest.mark.parametrize(
    "current_weight, target_weight, order_side, position_effect",
    [
        (0.0, 0.2, OrderSide.BUY, PositionEffect.OPEN_LONG),
        (0.2, 0.5, OrderSide.BUY, PositionEffect.INCREASE_LONG),
        (0.5, 0.2, OrderSide.SELL, PositionEffect.REDUCE_LONG),
        (0.2, 0.0, OrderSide.SELL, PositionEffect.CLOSE_LONG),
        (0.0, -0.2, OrderSide.SELL, PositionEffect.OPEN_SHORT),
        (-0.2, -0.5, OrderSide.SELL, PositionEffect.INCREASE_SHORT),
        (-0.5, -0.2, OrderSide.BUY, PositionEffect.REDUCE_SHORT),
        (-0.2, 0.0, OrderSide.BUY, PositionEffect.CLOSE_SHORT),
        (0.3, -0.2, OrderSide.SELL, PositionEffect.REVERSE_LONG_TO_SHORT),
        (-0.3, 0.2, OrderSide.BUY, PositionEffect.REVERSE_SHORT_TO_LONG),
        (0.0, 0.0, OrderSide.NONE, PositionEffect.NO_ACTION),
        (0.2, 0.2, OrderSide.NONE, PositionEffect.NO_ACTION),
        (-0.2, -0.2, OrderSide.NONE, PositionEffect.NO_ACTION),
    ],
)
def test_resolve_execution_action_derives_orders_from_current_and_target_exposure(
    current_weight: float,
    target_weight: float,
    order_side: OrderSide,
    position_effect: PositionEffect,
) -> None:
    action = resolve_execution_action(current_weight, target_weight)

    assert action.current_weight == current_weight
    assert action.target_weight == target_weight
    assert action.delta_weight == pytest.approx(target_weight - current_weight)
    assert action.current_side is target_side_from_weight(current_weight)
    assert action.target_side is target_side_from_weight(target_weight)
    assert action.order_side is order_side
    assert action.position_effect is position_effect


def test_resolve_execution_action_treats_tiny_delta_as_no_action() -> None:
    action = resolve_execution_action(0.1, 0.1 + 1e-13)

    assert action.order_side is OrderSide.NONE
    assert action.position_effect is PositionEffect.NO_ACTION
