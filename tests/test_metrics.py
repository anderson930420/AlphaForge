from __future__ import annotations

import math

import pandas as pd

from alphaforge.metrics import _compute_sharpe_ratio, compute_metrics


def test_compute_metrics_returns_expected_fields() -> None:
    equity_curve = pd.DataFrame(
        {
            "strategy_return": [0.0, 0.01, -0.005, 0.02],
            "equity": [100.0, 101.0, 100.495, 102.5049],
            "turnover": [0.0, 1.0, 0.0, 1.0],
        }
    )
    trades = pd.DataFrame({"net_pnl": [0.01, -0.005, 0.02]})

    metrics = compute_metrics(equity_curve, trades, annualization_factor=252)

    assert math.isclose(metrics.total_return, 0.025049, rel_tol=1e-6)
    assert metrics.trade_count == 3
    assert metrics.bar_count == 4
    assert math.isclose(metrics.win_rate, 2 / 3, rel_tol=1e-6)
    assert math.isclose(metrics.turnover, 2.0, rel_tol=1e-9)
    assert metrics.max_drawdown < 0


def test_compute_metrics_keeps_backward_compatible_zero_risk_free_default() -> None:
    equity_curve = pd.DataFrame(
        {
            "strategy_return": [0.0, 0.01, -0.005, 0.02],
            "equity": [100.0, 101.0, 100.495, 102.5049],
            "turnover": [0.0, 1.0, 0.0, 1.0],
        }
    )
    trades = pd.DataFrame({"net_pnl": [0.01, -0.005, 0.02]})

    default_metrics = compute_metrics(equity_curve, trades, annualization_factor=252)
    explicit_zero_metrics = compute_metrics(equity_curve, trades, annualization_factor=252, risk_free_rate=0.0)

    assert math.isclose(default_metrics.sharpe_ratio, explicit_zero_metrics.sharpe_ratio, rel_tol=1e-9)


def test_compute_sharpe_ratio_subtracts_per_period_risk_free_rate() -> None:
    returns = pd.Series([0.01, 0.02, 0.03])

    sharpe_ratio = _compute_sharpe_ratio(returns, annualization_factor=252, risk_free_rate=0.01)
    expected_std = float((returns - 0.01).std(ddof=1))
    expected = float((((returns - 0.01).mean()) / expected_std) * math.sqrt(252))

    assert math.isclose(sharpe_ratio, expected, rel_tol=1e-9)


def test_compute_sharpe_ratio_returns_zero_for_short_or_degenerate_series() -> None:
    assert _compute_sharpe_ratio(pd.Series([0.01]), annualization_factor=252) == 0.0
    assert _compute_sharpe_ratio(pd.Series([0.01, 0.01]), annualization_factor=252) == 0.0
    assert _compute_sharpe_ratio(pd.Series([float("nan"), float("nan")]), annualization_factor=252) == 0.0
