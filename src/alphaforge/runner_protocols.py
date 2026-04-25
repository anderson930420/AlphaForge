from __future__ import annotations

"""Shared runner-only protocol helpers.

This module owns orchestration scaffolding reused across multiple runner
workflows. It does not own execution semantics, search semantics, evidence
policy, persistence schemas, or presentation behavior.
"""

from pathlib import Path

import pandas as pd

from . import config
from .policy_types import ParameterGrid
from .schemas import BacktestConfig, StrategySpec
from .strategy.base import Strategy
from .strategy_registry import build_strategy_from_registry, get_strategy_registration


def resolve_backtest_config(backtest_config: BacktestConfig | None) -> BacktestConfig:
    """Materialize a concrete backtest config for runner workflows."""
    return backtest_config or BacktestConfig(
        initial_capital=config.INITIAL_CAPITAL,
        fee_rate=config.DEFAULT_FEE_RATE,
        slippage_rate=config.DEFAULT_SLIPPAGE_RATE,
        annualization_factor=config.DEFAULT_ANNUALIZATION,
    )


def workflow_root(output_dir: Path | None, experiment_name: str) -> Path | None:
    """Build the root directory for a named workflow when persistence is enabled."""
    return (output_dir / experiment_name) if output_dir is not None else None


def build_execution_metadata(market_data: pd.DataFrame, benchmark_summary: dict[str, float]) -> dict[str, object]:
    """Assemble runner-local execution metadata from canonical owners."""
    metadata: dict[str, object] = {
        "missing_data_policy": market_data.attrs.get("missing_data_policy", ""),
        "benchmark_summary": benchmark_summary,
    }
    metadata.update(build_holdout_metadata(market_data))
    return metadata


def build_strategy(strategy_spec: StrategySpec) -> Strategy:
    """Dispatch the supported strategy families from a canonical strategy spec."""
    return build_strategy_from_registry(strategy_spec)


def split_market_data_by_ratio(market_data: pd.DataFrame, split_ratio: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split market data chronologically into train and test segments."""
    if split_ratio <= 0.0 or split_ratio >= 1.0:
        raise ValueError("split_ratio must be between 0 and 1")

    split_index = int(len(market_data) * split_ratio)
    if split_index <= 0 or split_index >= len(market_data):
        raise ValueError("split_ratio creates an empty train or test segment")

    train_data = market_data.iloc[:split_index].reset_index(drop=True)
    test_data = market_data.iloc[split_index:].reset_index(drop=True)
    train_data.attrs.update(market_data.attrs)
    test_data.attrs.update(market_data.attrs)
    if train_data.empty or test_data.empty:
        raise ValueError("split_ratio creates an empty train or test segment")
    return train_data, test_data


def build_holdout_metadata(market_data: pd.DataFrame) -> dict[str, object]:
    """Extract holdout metadata from a market-data frame when available."""
    holdout_cutoff_date = market_data.attrs.get("holdout_cutoff_date")
    if holdout_cutoff_date is None:
        return {}
    return {
        "holdout_cutoff_date": holdout_cutoff_date,
        "development_rows": int(market_data.attrs.get("development_rows", len(market_data))),
        "holdout_rows": int(market_data.attrs.get("holdout_rows", 0)),
    }


def validate_train_windows(strategy_name: str, train_data: pd.DataFrame, parameter_grid: ParameterGrid) -> None:
    """Ensure the train segment can support the requested family-specific history length."""
    registration = get_strategy_registration(strategy_name)
    requested_windows = [
        (parameter_name, int(value))
        for parameter_name in registration.integer_window_parameters
        for value in parameter_grid.get(parameter_name, [])
    ]
    if not requested_windows:
        return
    required_parameter_name, largest_window = max(requested_windows, key=lambda item: item[1])
    if len(train_data) < largest_window:
        raise ValueError(f"Train segment is too short for the requested {required_parameter_name} values")


def build_validation_metadata(train_data: pd.DataFrame, test_data: pd.DataFrame) -> dict[str, object]:
    """Assemble runner-local metadata describing a train/test split."""
    metadata: dict[str, object] = {
        "train_rows": int(len(train_data)),
        "test_rows": int(len(test_data)),
        "train_start": str(train_data["datetime"].iloc[0]),
        "train_end": str(train_data["datetime"].iloc[-1]),
        "test_start": str(test_data["datetime"].iloc[0]),
        "test_end": str(test_data["datetime"].iloc[-1]),
    }
    metadata.update(build_holdout_metadata(train_data))
    return metadata


def generate_walk_forward_folds(
    market_data: pd.DataFrame,
    train_size: int,
    test_size: int,
    step_size: int,
) -> list[tuple[int, int, int]]:
    """Generate contiguous walk-forward fold index boundaries."""
    if train_size <= 0 or test_size <= 0 or step_size <= 0:
        raise ValueError("train_size, test_size, and step_size must be positive integers")
    if len(market_data) < train_size + test_size:
        raise ValueError("Dataset is too short for the requested train/test walk-forward windows")

    folds: list[tuple[int, int, int]] = []
    start_index = 0
    while start_index + train_size + test_size <= len(market_data):
        train_end_idx = start_index + train_size
        test_end_idx = train_end_idx + test_size
        folds.append((start_index, train_end_idx, test_end_idx))
        start_index += step_size
    return folds

