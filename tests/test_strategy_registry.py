from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from alphaforge.runner_protocols import build_strategy, validate_train_windows
from alphaforge.runner_workflows import run_strategy_comparison_with_details_workflow
from alphaforge.schemas import (
    BacktestConfig,
    DataSpec,
    StrategyComparisonConfig,
    StrategyFamilySearchConfig,
    StrategySpec,
    ValidationSplitConfig,
)
from alphaforge.search import evaluate_strategy_search_space
from alphaforge.strategy.breakout import BreakoutStrategy
from alphaforge.strategy.ma_crossover import MovingAverageCrossoverStrategy
from alphaforge.strategy_registry import (
    build_strategy_from_registry,
    get_strategy_registration,
    supported_strategy_families,
    validate_parameter_grid_for_strategy,
)


def test_supported_strategy_families_are_exact_current_registry_set() -> None:
    assert supported_strategy_families() == ("ma_crossover", "breakout")


def test_registry_exposes_expected_ma_parameter_metadata() -> None:
    registration = get_strategy_registration("ma_crossover")

    assert registration.name == "ma_crossover"
    assert registration.parameter_names == ("short_window", "long_window")
    assert registration.integer_window_parameters == ("long_window",)


def test_registry_exposes_expected_breakout_parameter_metadata() -> None:
    registration = get_strategy_registration("breakout")

    assert registration.name == "breakout"
    assert registration.parameter_names == ("lookback_window",)
    assert registration.integer_window_parameters == ("lookback_window",)


def test_registry_unknown_strategy_error_names_supported_families() -> None:
    with pytest.raises(ValueError) as exc_info:
        get_strategy_registration("unknown_strategy")

    message = str(exc_info.value)
    assert "unknown_strategy" in message
    assert "ma_crossover" in message
    assert "breakout" in message


def test_registry_parameter_grid_validator_accepts_valid_existing_family_grids() -> None:
    validate_parameter_grid_for_strategy("ma_crossover", {"short_window": [2], "long_window": [4]})
    validate_parameter_grid_for_strategy("breakout", {"lookback_window": [3]})


def test_registry_parameter_grid_validator_rejects_missing_required_keys() -> None:
    with pytest.raises(ValueError) as exc_info:
        validate_parameter_grid_for_strategy("ma_crossover", {"short_window": [2]})

    message = str(exc_info.value)
    assert "ma_crossover" in message
    assert "long_window" in message
    assert "missing required parameters" in message


def test_registry_parameter_grid_validator_rejects_unexpected_keys() -> None:
    with pytest.raises(ValueError) as exc_info:
        validate_parameter_grid_for_strategy(
            "ma_crossover",
            {"short_window": [5], "long_window": [20], "threshold": [0.01]},
        )

    message = str(exc_info.value)
    assert "ma_crossover" in message
    assert "threshold" in message
    assert "unexpected parameters" in message


def test_registry_backed_construction_matches_existing_strategy_behavior() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=5, freq="D"),
            "open": [10.0, 11.0, 12.0, 13.0, 14.0],
            "high": [10.5, 11.5, 12.5, 13.5, 14.5],
            "low": [9.5, 10.5, 11.5, 12.5, 13.5],
            "close": [10.0, 11.0, 12.0, 13.0, 14.0],
            "volume": [100, 110, 120, 130, 140],
        }
    )
    ma_spec = StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 3})
    breakout_spec = StrategySpec(name="breakout", parameters={"lookback_window": 2})

    ma_strategy = build_strategy_from_registry(ma_spec)
    breakout_strategy = build_strategy_from_registry(breakout_spec)

    assert isinstance(ma_strategy, MovingAverageCrossoverStrategy)
    assert isinstance(breakout_strategy, BreakoutStrategy)
    assert ma_strategy.generate_signals(market_data).equals(MovingAverageCrossoverStrategy(ma_spec).generate_signals(market_data))
    assert breakout_strategy.generate_signals(market_data).equals(BreakoutStrategy(breakout_spec).generate_signals(market_data))
    assert isinstance(build_strategy(ma_spec), MovingAverageCrossoverStrategy)


def test_search_space_evaluation_uses_registry_for_existing_families() -> None:
    ma_evaluation = evaluate_strategy_search_space("ma_crossover", {"short_window": [2], "long_window": [3]})
    breakout_evaluation = evaluate_strategy_search_space("breakout", {"lookback_window": [2]})

    assert ma_evaluation.parameter_names == ("short_window", "long_window")
    assert [spec.name for spec in ma_evaluation.strategy_specs] == ["ma_crossover"]
    assert breakout_evaluation.parameter_names == ("lookback_window",)
    assert [spec.name for spec in breakout_evaluation.strategy_specs] == ["breakout"]


def test_search_space_evaluation_rejects_invalid_grids_through_registry_validator() -> None:
    with pytest.raises(ValueError, match="ma_crossover.*long_window"):
        evaluate_strategy_search_space("ma_crossover", {"short_window": [2]})

    with pytest.raises(ValueError, match="ma_crossover.*threshold"):
        evaluate_strategy_search_space(
            "ma_crossover",
            {"short_window": [2], "long_window": [4], "threshold": [0.01]},
        )


def test_strategy_comparison_rejects_invalid_family_grid_before_expensive_execution(
    sample_market_csv: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("expensive validation should not start for invalid family grids")

    monkeypatch.setattr("alphaforge.runner_workflows.run_validate_search_on_market_data", fail_if_called)

    config = StrategyComparisonConfig(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        split_config=ValidationSplitConfig(split_ratio=0.5),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        strategy_families=[
            StrategyFamilySearchConfig(
                strategy_name="ma_crossover",
                parameter_grid={"short_window": [2], "long_window": [4], "threshold": [0.01]},
            )
        ],
    )

    with pytest.raises(ValueError, match="ma_crossover.*threshold"):
        run_strategy_comparison_with_details_workflow(config)


def test_train_window_validation_uses_registry_integer_window_metadata() -> None:
    train_data = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=3, freq="D")})

    with pytest.raises(ValueError, match="long_window"):
        validate_train_windows("ma_crossover", train_data, {"short_window": [2], "long_window": [5]})
    with pytest.raises(ValueError, match="lookback_window"):
        validate_train_windows("breakout", train_data, {"lookback_window": [5]})


def test_no_stale_supported_strategy_family_source_outside_registry() -> None:
    source_root = Path(__file__).resolve().parents[1] / "src" / "alphaforge"
    offenders = [
        path
        for path in source_root.rglob("*.py")
        if path.name != "strategy_registry.py" and "SUPPORTED_STRATEGY_FAMILIES" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_schemas_do_not_import_strategy_registry() -> None:
    source_root = Path(__file__).resolve().parents[1] / "src" / "alphaforge"
    schemas_source = (source_root / "schemas.py").read_text(encoding="utf-8")

    assert "strategy_registry" not in schemas_source


def test_search_delegates_parameter_grid_key_validation_to_registry() -> None:
    source_root = Path(__file__).resolve().parents[1] / "src" / "alphaforge"
    search_source = (source_root / "search.py").read_text(encoding="utf-8")

    assert "_validate_search_parameter_grid" not in search_source
    assert "validate_parameter_grid_for_strategy(strategy_name, parameter_grid)" in search_source
    assert "missing =" not in search_source
    assert "unexpected =" not in search_source
    assert "expected = set" not in search_source
    assert "provided = set" not in search_source
