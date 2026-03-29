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

# AlphaForge intentionally uses pandas.DataFrame as the equity-curve interface.
# The frame is expected to contain at least datetime, position, turnover,
# strategy_return, and equity columns after backtest execution.
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
