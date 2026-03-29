from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from alphaforge.report import render_experiment_report, save_experiment_report
from alphaforge.schemas import BacktestConfig, DataSpec, ExperimentResult, MetricReport, StrategySpec

pytest.importorskip("plotly")


def test_render_and_save_experiment_report_creates_html(tmp_path: Path) -> None:
    result = ExperimentResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 5, "long_window": 20}),
        backtest_config=BacktestConfig(
            initial_capital=100000.0,
            fee_rate=0.001,
            slippage_rate=0.0005,
            annualization_factor=252,
        ),
        metrics=MetricReport(
            total_return=0.20,
            annualized_return=0.31,
            sharpe_ratio=1.23,
            max_drawdown=-0.08,
            win_rate=0.55,
            turnover=1.5,
            trade_count=4,
        ),
        score=1.0,
    )
    equity_curve = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=4, freq="D"),
            "close": [1000.0, 1010.0, 995.0, 1035.0],
            "equity": [100000.0, 101000.0, 99000.0, 103000.0],
        }
    )
    trades = pd.DataFrame(
        {
            "entry_time": ["2024-01-02 00:00:00"],
            "exit_time": ["2024-01-04 00:00:00"],
            "entry_price": [1010.0],
            "exit_price": [1035.0],
        }
    )

    report_content = render_experiment_report(result, equity_curve, trades)
    output_path = save_experiment_report(report_content, tmp_path / "report.html")

    assert output_path.exists()
    saved_content = output_path.read_text(encoding="utf-8")
    assert "Metrics Summary" in saved_content
    assert "Total Return" in saved_content
    assert "Annualized Return" in saved_content
    assert "Sharpe Ratio" in saved_content
    assert "Max Drawdown" in saved_content
    assert "Win Rate" in saved_content
    assert "Turnover" in saved_content
    assert "Trade Count" in saved_content
    assert "Equity Curve" in saved_content
    assert "Drawdown" in saved_content
    assert "Price with Trade Markers" in saved_content
    assert "Close Price" in saved_content
    assert "Buy" in saved_content
    assert "Sell" in saved_content
    assert "https://cdn.plot.ly" not in saved_content
    assert saved_content.count("Plotly.newPlot") == 3


def test_render_experiment_report_handles_empty_trades_with_price_section() -> None:
    result = ExperimentResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 5, "long_window": 20}),
        backtest_config=BacktestConfig(
            initial_capital=100000.0,
            fee_rate=0.001,
            slippage_rate=0.0005,
            annualization_factor=252,
        ),
        metrics=MetricReport(
            total_return=0.20,
            annualized_return=0.31,
            sharpe_ratio=1.23,
            max_drawdown=-0.08,
            win_rate=0.55,
            turnover=1.5,
            trade_count=0,
        ),
        score=1.0,
    )
    equity_curve = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=3, freq="D"),
            "close": [1000.0, 1005.0, 1012.0],
            "equity": [100000.0, 100500.0, 101200.0],
        }
    )

    report_content = render_experiment_report(result, equity_curve, pd.DataFrame())

    assert "Price with Trade Markers" in report_content
    assert "Close Price" in report_content
    assert "https://cdn.plot.ly" not in report_content
