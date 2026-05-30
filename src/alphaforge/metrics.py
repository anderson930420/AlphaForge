"""Canonical strategy-metric formulas for AlphaForge runtime outputs.

This module consumes backtest-owned runtime artifacts and turns them into the
strategy metric summary. It does not define execution timing, benchmark logic,
plotting semantics, or persisted artifact layout.

Signed execution can theoretically drive equity to or below zero. In that case,
annualized return is undefined and drawdown semantics may be difficult to
interpret. AlphaForge reports annualized_return as None with an explicit status
instead of clamping or fabricating a numeric value.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .schemas import MetricReport


def compute_metrics(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    annualization_factor: int,
    risk_free_rate: float = 0.0,
) -> MetricReport:
    if equity_curve.empty:
        raise ValueError("equity_curve must contain at least one row to compute metrics")
    returns = equity_curve["strategy_return"].astype(float)
    bar_count = int(len(equity_curve))
    initial_equity = float(equity_curve["equity"].iloc[0])
    ending_equity = float(equity_curve["equity"].iloc[-1])
    total_return = _compute_total_return(initial_equity=initial_equity, ending_equity=ending_equity)
    periods = max(len(equity_curve) - 1, 1)
    annualized_return, annualized_return_status = _compute_annualized_return(
        initial_equity=initial_equity,
        ending_equity=ending_equity,
        total_return=total_return,
        annualization_factor=annualization_factor,
        periods=periods,
    )
    sharpe_ratio = _compute_sharpe_ratio(returns, annualization_factor, risk_free_rate=risk_free_rate)
    max_drawdown = _compute_max_drawdown(equity_curve["equity"])
    trade_count = int(len(trades))
    win_rate = float((trades["trade_net_return"] > 0).mean()) if trade_count else 0.0
    turnover = float(equity_curve["turnover"].sum())
    return MetricReport(
        total_return=total_return,
        annualized_return=annualized_return,
        annualized_return_status=annualized_return_status,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        turnover=turnover,
        bar_count=bar_count,
        trade_count=trade_count,
    )


def _compute_total_return(*, initial_equity: float, ending_equity: float) -> float:
    if initial_equity == 0:
        return float("nan")
    return (ending_equity / initial_equity) - 1.0


def _compute_annualized_return(
    *,
    initial_equity: float,
    ending_equity: float,
    total_return: float,
    annualization_factor: int,
    periods: int,
) -> tuple[float | None, str]:
    if initial_equity <= 0:
        return None, "undefined_non_positive_initial_equity"
    if ending_equity <= 0:
        return None, "undefined_non_positive_ending_equity"
    return (1.0 + total_return) ** (annualization_factor / periods) - 1.0, "ok"


def _compute_sharpe_ratio(returns: pd.Series, annualization_factor: int, risk_free_rate: float = 0.0) -> float:
    excess_returns = returns.astype(float) - float(risk_free_rate)
    if len(excess_returns) < 2:
        return 0.0
    std = float(excess_returns.std(ddof=1))
    if not np.isfinite(std) or math.isclose(std, 0.0):
        return 0.0
    return float((excess_returns.mean() / std) * math.sqrt(annualization_factor))


def _compute_max_drawdown(equity: pd.Series) -> float:
    running_max = equity.cummax()
    drawdown = (equity / running_max) - 1.0
    return float(drawdown.min())
