from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from alphaforge.report import (
    ExperimentReportInput,
    SearchReportLinkContext,
    build_experiment_report_input,
    build_search_report_link_context,
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
    quality_summary = {
        "required_columns": ["datetime", "open", "high", "low", "close", "volume"],
        "canonical_column_order": ["datetime", "open", "high", "low", "close", "volume"],
        "datetime_policy": "parse_sort_keep_last",
        "duplicate_datetime_policy": "deterministic_keep_last",
        "missing_ohlc_policy": "fail",
        "missing_volume_policy": "fill_zero",
        "missing_data_policy": "Drop rows with missing datetime or OHLC values; keep the last row for duplicate datetimes after sorting, and fill missing volume with 0.",
        "source_row_count": 4,
        "duplicate_row_count": 0,
        "accepted_row_count": 4,
        "volume_missing_row_count": 0,
    }
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
            trade_count=4, bar_count=1),
        score=1.0,
        metadata={"data_quality_summary": quality_summary},
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
            "entry_datetime": ["2024-01-02 00:00:00"],
            "exit_datetime": ["2024-01-04 00:00:00"],
            "entry_price": [1010.0],
            "exit_price": [1035.0],
            "holding_period": [1],
            "trade_gross_return": [0.024752475247524754],
            "trade_net_return": [0.024252475247524754],
            "cost_return_contribution": [0.0005],
            "entry_target_position": [1.0],
            "exit_target_position": [0.0],
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
    assert "Execution Assumptions" in saved_content
    assert "Market Data Quality" in saved_content
    assert "Trade Return Semantics" in saved_content
    assert "trade_net_return" in saved_content
    assert "cost_return_contribution" in saved_content
    assert "trade_net_return &gt; 0" in saved_content
    assert "dollar PnL" not in saved_content
    assert "legacy_close_to_close_lagged" in saved_content
    assert "position[t] = target_position[t-1]" in saved_content
    assert "close_to_close" in saved_content
    assert "[0.0, 1.0]" in saved_content
    assert "False" in saved_content
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
    assert "deterministic_keep_last" in saved_content
    assert "fill_zero" in saved_content
    _assert_no_external_plotly_cdn_script(saved_content)
    assert "Plotly.newPlot" in saved_content
    assert saved_content.count('class="plotly-graph-div"') == 4


def test_render_experiment_report_shows_custom_signal_metadata(tmp_path: Path) -> None:
    result = ExperimentResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        strategy_spec=StrategySpec(name="custom_signal", parameters={}),
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
            bar_count=1,
        ),
        score=1.0,
        metadata={
            "signal_file": "/tmp/custom_signal.csv",
            "signal_name": "signalforge_moskowitz",
            "source": "SignalForge",
            "symbol": "2330",
            "signal_row_count": 16,
        },
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
            "entry_datetime": ["2024-01-02 00:00:00"],
            "exit_datetime": ["2024-01-04 00:00:00"],
            "entry_price": [1010.0],
            "exit_price": [1035.0],
            "holding_period": [1],
            "trade_gross_return": [0.024752475247524754],
            "trade_net_return": [0.024252475247524754],
            "cost_return_contribution": [0.0005],
            "entry_target_position": [1.0],
            "exit_target_position": [0.0],
        }
    )
    report_input = ExperimentReportInput(
        result=result,
        equity_curve=equity_curve,
        trades=trades,
        benchmark_summary=summarize_buy_and_hold(equity_curve, result.backtest_config.initial_capital),
        benchmark_curve=build_buy_and_hold_equity_curve(equity_curve, result.backtest_config.initial_capital),
    )

    html = render_experiment_report(report_input)
    output_path = save_experiment_report(html, tmp_path / "custom_signal_report.html")
    saved_content = output_path.read_text(encoding="utf-8")

    assert "custom_signal" in saved_content
    assert "Signal Metadata" in saved_content
    assert "signalforge_moskowitz" in saved_content
    assert "SignalForge" in saved_content
    assert "/tmp/custom_signal.csv" in saved_content
    assert "16" in saved_content


def test_build_experiment_report_input_preserves_canonical_fields() -> None:
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
            trade_count=4, bar_count=1),
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
            "entry_datetime": ["2024-01-02 00:00:00"],
            "exit_datetime": ["2024-01-04 00:00:00"],
            "entry_price": [1010.0],
            "exit_price": [1035.0],
            "holding_period": [1],
            "trade_gross_return": [0.024752475247524754],
            "trade_net_return": [0.024252475247524754],
            "cost_return_contribution": [0.0005],
            "entry_target_position": [1.0],
            "exit_target_position": [0.0],
        }
    )

    report_input = build_experiment_report_input(
        result=result,
        equity_curve=equity_curve,
        trades=trades,
        benchmark_summary={"total_return": 0.05, "max_drawdown": -0.02},
        benchmark_curve=equity_curve,
    )

    assert report_input.result == result
    assert report_input.equity_curve.equals(equity_curve)
    assert report_input.trades.equals(trades)
    assert report_input.benchmark_summary == {"total_return": 0.05, "max_drawdown": -0.02}


def test_build_search_report_link_context_uses_root_display_name(tmp_path: Path) -> None:
    search_root = tmp_path / "search_case"
    search_root.mkdir()

    link_context = build_search_report_link_context(search_root)

    assert link_context.link_base_dir == search_root
    assert link_context.search_display_name == "search_case"


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
            trade_count=0, bar_count=1),
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

    assert "Execution Assumptions" in report_content
    assert "Trade Return Semantics" in report_content
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
    quality_summary = {
        "required_columns": ["datetime", "open", "high", "low", "close", "volume"],
        "canonical_column_order": ["datetime", "open", "high", "low", "close", "volume"],
        "datetime_policy": "parse_sort_keep_last",
        "duplicate_datetime_policy": "deterministic_keep_last",
        "missing_ohlc_policy": "fail",
        "missing_volume_policy": "fill_zero",
        "missing_data_policy": "Drop rows with missing datetime or OHLC values; keep the last row for duplicate datetimes after sorting, and fill missing volume with 0.",
        "source_row_count": 3,
        "duplicate_row_count": 0,
        "accepted_row_count": 3,
        "volume_missing_row_count": 0,
    }
    ranked_results = [
        ExperimentResult(
            data_spec=DataSpec(path=Path("sample_data/a.csv"), symbol="2330"),
            strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
            backtest_config=BacktestConfig(100000.0, 0.001, 0.0005, 252),
            metrics=MetricReport(0.2, 0.3, 1.4, -0.08, 0.6, 1.2, 4, bar_count=1),
            score=0.9,
            metadata={"data_quality_summary": quality_summary},
        ),
        ExperimentResult(
            data_spec=DataSpec(path=Path("sample_data/b.csv"), symbol="2330"),
            strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 3, "long_window": 5}),
            backtest_config=BacktestConfig(100000.0, 0.001, 0.0005, 252),
            metrics=MetricReport(0.18, 0.28, 1.2, -0.1, 0.55, 1.1, 3, bar_count=1),
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
    assert "Execution Assumptions" in report_content
    assert "Market Data Quality" in report_content
    assert "Trade Return Semantics" in report_content
    assert "Ranked Comparison" in report_content
    assert "Short Window" in report_content
    assert "Long Window" in report_content
    assert "Top Equity Curves" in report_content
    assert "Top Drawdowns" in report_content
    assert "runs/run_001" in report_content
    assert "best_report.html" in report_content
    assert "deterministic_keep_last" in report_content
    assert "dollar PnL" not in report_content
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
            metrics=MetricReport(0.2, 0.3, 1.4, -0.08, 0.6, 1.2, 4, bar_count=1),
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
    assert "Execution Assumptions" in report_content
    assert "Trade Return Semantics" in report_content


def test_render_search_comparison_report_supports_breakout_parameter_labels(tmp_path: Path) -> None:
    link_base_dir = tmp_path / "breakout_case"
    link_base_dir.mkdir()
    ranked_results = [
        ExperimentResult(
            data_spec=DataSpec(path=Path("sample_data/a.csv"), symbol="2330"),
            strategy_spec=StrategySpec(name="breakout", parameters={"lookback_window": 10}),
            backtest_config=BacktestConfig(100000.0, 0.001, 0.0005, 252),
            metrics=MetricReport(0.2, 0.3, 1.4, -0.08, 0.6, 1.2, 4, bar_count=1),
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
            search_display_name="breakout_case",
        ),
        ranked_results=ranked_results,
        artifact_receipts=artifact_receipts,
        top_equity_curves={},
    )

    assert "Lookback Window" in report_content
    assert "lookback_window" not in report_content


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
