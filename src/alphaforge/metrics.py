from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .schemas import MetricReport


def compute_metrics(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    annualization_factor: int,
) -> MetricReport:
    returns = equity_curve["strategy_return"].astype(float)
    total_return = (equity_curve["equity"].iloc[-1] / equity_curve["equity"].iloc[0]) - 1.0
    periods = max(len(equity_curve) - 1, 1)
    annualized_return = (1.0 + total_return) ** (annualization_factor / periods) - 1.0
    sharpe_ratio = _compute_sharpe_ratio(returns, annualization_factor)
    max_drawdown = _compute_max_drawdown(equity_curve["equity"])
    trade_count = int(len(trades))
    win_rate = float((trades["net_pnl"] > 0).mean()) if trade_count else 0.0
    turnover = float(equity_curve["turnover"].sum())
    return MetricReport(
        total_return=total_return,
        annualized_return=annualized_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        turnover=turnover,
        trade_count=trade_count,
    )


def _compute_sharpe_ratio(returns: pd.Series, annualization_factor: int) -> float:
    std = float(returns.std(ddof=0))
    if math.isclose(std, 0.0):
        return 0.0
    return float((returns.mean() / std) * math.sqrt(annualization_factor))


def _compute_max_drawdown(equity: pd.Series) -> float:
    running_max = equity.cummax()
    drawdown = (equity / running_max) - 1.0
    return float(drawdown.min())
