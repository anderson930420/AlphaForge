from __future__ import annotations

import math

import pandas as pd

from alphaforge.metrics import compute_metrics


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
    assert math.isclose(metrics.win_rate, 2 / 3, rel_tol=1e-6)
    assert math.isclose(metrics.turnover, 2.0, rel_tol=1e-9)
    assert metrics.max_drawdown < 0
