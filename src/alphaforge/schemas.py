from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

BACKTEST_EQUITY_CURVE_REQUIRED_COLUMNS = (
    "datetime",
    "position",
    "turnover",
    "strategy_return",
    "equity",
)

# AlphaForge intentionally uses pandas.DataFrame as the equity-curve interface.
# The standard backtest artifact is expected to contain at least the columns in
# BACKTEST_EQUITY_CURVE_REQUIRED_COLUMNS after backtest execution.
EquityCurveFrame = pd.DataFrame


@dataclass(frozen=True)
class DataSpec:
    path: Path
    symbol: str = "UNKNOWN"
    datetime_column: str = "datetime"


@dataclass(frozen=True)
class StrategySpec:
    name: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float
    fee_rate: float
    slippage_rate: float
    annualization_factor: int = 252


@dataclass(frozen=True)
class TradeRecord:
    entry_time: str
    exit_time: str
    side: str
    quantity: float
    entry_price: float
    exit_price: float
    gross_return: float
    net_pnl: float


@dataclass(frozen=True)
class MetricReport:
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    turnover: float
    trade_count: int


@dataclass(frozen=True)
class ExperimentResult:
    data_spec: DataSpec
    strategy_spec: StrategySpec
    backtest_config: BacktestConfig
    metrics: MetricReport
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationSplitConfig:
    split_ratio: float


@dataclass(frozen=True)
class ValidationResult:
    data_spec: DataSpec
    split_config: ValidationSplitConfig
    selected_strategy_spec: StrategySpec
    train_best_result: ExperimentResult
    test_result: ExperimentResult
    test_benchmark_summary: dict[str, float] = field(default_factory=dict)
    train_ranked_results_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WalkForwardConfig:
    train_size: int
    test_size: int
    step_size: int


@dataclass(frozen=True)
class WalkForwardFoldResult:
    fold_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    selected_strategy_spec: StrategySpec
    train_best_result: ExperimentResult
    test_result: ExperimentResult
    test_benchmark_summary: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class WalkForwardResult:
    data_spec: DataSpec
    walk_forward_config: WalkForwardConfig
    folds: list[WalkForwardFoldResult]
    aggregate_test_metrics: dict[str, float | int]
    aggregate_benchmark_metrics: dict[str, float | int] = field(default_factory=dict)
    walk_forward_summary_path: Path | None = None
    fold_results_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
