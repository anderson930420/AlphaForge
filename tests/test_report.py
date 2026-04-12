from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from alphaforge.report import (
    ExperimentReportInput,
    SearchReportLinkContext,
    render_experiment_report,
    render_search_comparison_report,
    save_experiment_report,
)
from alphaforge.benchmark import build_buy_and_hold_equity_curve, summarize_buy_and_hold
from alphaforge.schemas import BacktestConfig, DataSpec, ExperimentResult, MetricReport, StrategySpec
from alphaforge.storage import ArtifactReceipt

pytest.importorskip("plotly")


def _assert_no_external_plotly_cdn_script(html: str) -> None:
    assert 'src="https://cdn.plot.ly' not in html
    assert "src='https://cdn.plot.ly" not in html
    assert 'src="http://cdn.plot.ly' not in html
    assert "src='http://cdn.plot.ly" not in html


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

    report_input = ExperimentReportInput(
        result=result,
        equity_curve=equity_curve,
        trades=trades,
        benchmark_summary=summarize_buy_and_hold(equity_curve, result.backtest_config.initial_capital),
        benchmark_curve=build_buy_and_hold_equity_curve(equity_curve, result.backtest_config.initial_capital),
    )
    report_content = render_experiment_report(report_input)
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
    assert "Strategy vs Buy-and-Hold" in saved_content
    assert "Drawdown" in saved_content
    assert "Price with Trade Markers" in saved_content
    assert "Benchmark Return" in saved_content
    assert "Benchmark Max Drawdown" in saved_content
    assert "Excess Return" in saved_content
    assert "Buy and Hold" in saved_content
    assert "Close Price" in saved_content
    assert "Buy" in saved_content
    assert "Sell" in saved_content
    _assert_no_external_plotly_cdn_script(saved_content)
    assert "Plotly.newPlot" in saved_content
    assert saved_content.count('class="plotly-graph-div"') == 4


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

    report_input = ExperimentReportInput(
        result=result,
        equity_curve=equity_curve,
        trades=pd.DataFrame(),
        benchmark_summary=summarize_buy_and_hold(equity_curve, result.backtest_config.initial_capital),
        benchmark_curve=build_buy_and_hold_equity_curve(equity_curve, result.backtest_config.initial_capital),
    )
    report_content = render_experiment_report(report_input)

    assert "Strategy vs Buy-and-Hold" in report_content
    assert "Benchmark Return" in report_content
    assert "Price with Trade Markers" in report_content
    assert "Buy and Hold" in report_content
    assert "Close Price" in report_content
    _assert_no_external_plotly_cdn_script(report_content)
    assert "Plotly.newPlot" in report_content


def test_render_search_comparison_report_includes_ranked_table_and_overlay_sections(tmp_path: Path) -> None:
    link_base_dir = tmp_path / "presentation_case"
    link_base_dir.mkdir()
    ranked_results = [
        ExperimentResult(
            data_spec=DataSpec(path=Path("sample_data/a.csv"), symbol="2330"),
            strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
            backtest_config=BacktestConfig(100000.0, 0.001, 0.0005, 252),
            metrics=MetricReport(0.2, 0.3, 1.4, -0.08, 0.6, 1.2, 4),
            score=0.9,
        ),
        ExperimentResult(
            data_spec=DataSpec(path=Path("sample_data/b.csv"), symbol="2330"),
            strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 3, "long_window": 5}),
            backtest_config=BacktestConfig(100000.0, 0.001, 0.0005, 252),
            metrics=MetricReport(0.18, 0.28, 1.2, -0.1, 0.55, 1.1, 3),
            score=0.8,
        ),
    ]
    artifact_receipts = [
        ArtifactReceipt(
            run_dir=link_base_dir / "runs" / "run_001",
            equity_curve_path=link_base_dir / "runs" / "run_001" / "equity_curve.csv",
            trade_log_path=link_base_dir / "runs" / "run_001" / "trade_log.csv",
            metrics_summary_path=link_base_dir / "runs" / "run_001" / "metrics_summary.json",
        ),
        ArtifactReceipt(
            run_dir=link_base_dir / "runs" / "run_002",
            equity_curve_path=link_base_dir / "runs" / "run_002" / "equity_curve.csv",
            trade_log_path=link_base_dir / "runs" / "run_002" / "trade_log.csv",
            metrics_summary_path=link_base_dir / "runs" / "run_002" / "metrics_summary.json",
        ),
    ]
    top_equity_curves = {
        "Rank 1 | SW 2 | LW 4": pd.DataFrame(
            {"datetime": pd.date_range("2024-01-01", periods=3, freq="D"), "equity": [100.0, 105.0, 110.0]}
        ),
        "Rank 2 | SW 3 | LW 5": pd.DataFrame(
            {"datetime": pd.date_range("2024-01-01", periods=3, freq="D"), "equity": [100.0, 103.0, 107.0]}
        ),
    }

    report_content = render_search_comparison_report(
        link_context=SearchReportLinkContext(
            link_base_dir=link_base_dir,
            search_display_name="Friendly Search Name",
        ),
        ranked_results=ranked_results,
        artifact_receipts=artifact_receipts,
        top_equity_curves=top_equity_curves,
        best_report_path=link_base_dir / "best_report.html",
    )

    assert "Friendly Search Name" in report_content
    assert "Ranked Comparison" in report_content
    assert "Short Window" in report_content
    assert "Long Window" in report_content
    assert "Top Equity Curves" in report_content
    assert "Top Drawdowns" in report_content
    assert "runs/run_001" in report_content
    assert "best_report.html" in report_content
    _assert_no_external_plotly_cdn_script(report_content)
    assert "Plotly.newPlot" in report_content


def test_render_search_comparison_report_omits_best_report_link_when_not_provided(tmp_path: Path) -> None:
    link_base_dir = tmp_path / "presentation_case"
    link_base_dir.mkdir()
    ranked_results = [
        ExperimentResult(
            data_spec=DataSpec(path=Path("sample_data/a.csv"), symbol="2330"),
            strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
            backtest_config=BacktestConfig(100000.0, 0.001, 0.0005, 252),
            metrics=MetricReport(0.2, 0.3, 1.4, -0.08, 0.6, 1.2, 4),
            score=0.9,
        )
    ]
    artifact_receipts = [
        ArtifactReceipt(
            run_dir=link_base_dir / "runs" / "run_001",
            equity_curve_path=link_base_dir / "runs" / "run_001" / "equity_curve.csv",
            trade_log_path=link_base_dir / "runs" / "run_001" / "trade_log.csv",
            metrics_summary_path=link_base_dir / "runs" / "run_001" / "metrics_summary.json",
        )
    ]

    report_content = render_search_comparison_report(
        link_context=SearchReportLinkContext(
            link_base_dir=link_base_dir,
            search_display_name="search_case",
        ),
        ranked_results=ranked_results,
        artifact_receipts=artifact_receipts,
        top_equity_curves={},
    )

    assert "runs/run_001" in report_content
    assert "best_report.html" not in report_content
    assert "search_case" in report_content


def test_render_search_comparison_report_handles_empty_ranked_results(tmp_path: Path) -> None:
    link_base_dir = tmp_path / "empty_search"
    link_base_dir.mkdir()

    report_content = render_search_comparison_report(
        link_context=SearchReportLinkContext(
            link_base_dir=link_base_dir,
            search_display_name="empty_search",
        ),
        ranked_results=[],
        artifact_receipts=[],
        top_equity_curves={},
    )

    assert "Ranked Comparison" in report_content
    assert "No ranked results available." in report_content
    assert "Top Equity Curves" not in report_content
