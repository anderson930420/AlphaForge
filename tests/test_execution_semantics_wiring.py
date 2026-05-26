from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.backtest import SIGNED_EXECUTION_SEMANTICS, run_backtest
from alphaforge.cli import build_parser
from alphaforge.evidence_diagnostics import compute_cost_sensitivity
from alphaforge.schemas import BacktestConfig


def _make_market_data(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=len(closes), freq="D"),
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [100 + index for index in range(len(closes))],
        }
    )


def test_run_backtest_uses_execution_semantics_from_config() -> None:
    market_data = _make_market_data([100, 90, 81])
    config = BacktestConfig(
        initial_capital=1000,
        fee_rate=0.0,
        slippage_rate=0.0,
        annualization_factor=252,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )

    equity_curve, _ = run_backtest(market_data, pd.Series([-1.0, -1.0, 0.0]), config)

    assert equity_curve["position"].tolist() == [0.0, -1.0, -1.0]
    assert equity_curve["strategy_return"].tolist() == pytest.approx([0.0, 0.10, 0.10])
    assert equity_curve.iloc[-1]["equity"] == pytest.approx(1210.0)


def test_cost_sensitivity_preserves_signed_execution_semantics() -> None:
    market_data = _make_market_data([100, 90, 81])
    config = BacktestConfig(
        initial_capital=1000,
        fee_rate=0.0,
        slippage_rate=0.0,
        annualization_factor=252,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )

    summary = compute_cost_sensitivity(
        market_data=market_data,
        target_positions=pd.Series([-1.0, -1.0, 0.0], index=market_data.index),
        backtest_config=config,
    )

    assert summary.base_cost.annualized_return > 0.0
    assert summary.base_cost.sharpe > 0.0


def test_research_validate_cli_accepts_execution_semantics() -> None:
    args = build_parser().parse_args(
        [
            "research-validate",
            "--data",
            "market.csv",
            "--strategy",
            "custom_signal",
            "--signal-file",
            "signal.csv",
            "--development-start",
            "2024-01-01",
            "--development-end",
            "2024-01-02",
            "--holdout-start",
            "2024-01-03",
            "--holdout-end",
            "2024-01-04",
            "--train-size",
            "2",
            "--test-size",
            "1",
            "--step-size",
            "1",
            "--execution-semantics",
            SIGNED_EXECUTION_SEMANTICS,
        ]
    )

    assert args.execution_semantics == SIGNED_EXECUTION_SEMANTICS
