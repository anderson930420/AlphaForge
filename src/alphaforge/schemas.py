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
