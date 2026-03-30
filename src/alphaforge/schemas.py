from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

TRADE_LOG_COLUMNS = [
    "entry_time",
    "exit_time",
    "side",
    "quantity",
    "entry_price",
    "exit_price",
    "gross_return",
    "net_pnl",
]

RANKED_RESULTS_BASE_COLUMNS = [
    "strategy",
    "total_return",
    "annualized_return",
    "sharpe_ratio",
    "max_drawdown",
    "win_rate",
    "turnover",
    "trade_count",
    "score",
]

BACKTEST_EQUITY_CURVE_REQUIRED_COLUMNS = (
    "datetime",
    "position",
    "turnover",
    "strategy_return",
    "equity",
)

REPORT_EQUITY_CURVE_REQUIRED_COLUMNS = (
    "datetime",
    "equity",
    "close",
)

# AlphaForge intentionally uses pandas.DataFrame as the equity-curve interface.
# The standard backtest artifact is expected to contain at least the columns in
# BACKTEST_EQUITY_CURVE_REQUIRED_COLUMNS after backtest execution.
# Report and visualization paths rely on a stronger shape that also includes
# close-price data, represented by REPORT_EQUITY_CURVE_REQUIRED_COLUMNS.
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
    equity_curve_path: Path | None = None
    trade_log_path: Path | None = None
    metrics_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("equity_curve_path", "trade_log_path", "metrics_path"):
            value = payload.get(key)
            payload[key] = str(value) if value else None
        payload["data_spec"]["path"] = str(self.data_spec.path)
        return payload


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
    validation_summary_path: Path | None = None
    train_ranked_results_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("validation_summary_path", "train_ranked_results_path"):
            value = payload.get(key)
            payload[key] = str(value) if value else None
        payload["data_spec"]["path"] = str(self.data_spec.path)
        return payload


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
    fold_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["fold_path"] = str(self.fold_path) if self.fold_path else None
        return payload


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "data_spec": {
                "path": str(self.data_spec.path),
                "symbol": self.data_spec.symbol,
                "datetime_column": self.data_spec.datetime_column,
            },
            "walk_forward_config": asdict(self.walk_forward_config),
            "folds": [fold.to_dict() for fold in self.folds],
            "aggregate_test_metrics": self.aggregate_test_metrics,
            "aggregate_benchmark_metrics": self.aggregate_benchmark_metrics,
            "walk_forward_summary_path": str(self.walk_forward_summary_path) if self.walk_forward_summary_path else None,
            "fold_results_path": str(self.fold_results_path) if self.fold_results_path else None,
            "metadata": self.metadata,
        }
