from __future__ import annotations

import sys
import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from alphaforge.cli import main
from alphaforge.experiment_runner import ExperimentExecutionOutput, SearchExecutionOutput
from alphaforge.report import ExperimentReportInput
from alphaforge.storage import ArtifactReceipt, SearchArtifactReceipt
from alphaforge.schemas import BacktestConfig, DataSpec, ExperimentResult, MetricReport, SearchSummary, StrategySpec


def _make_search_summary(results: list[ExperimentResult], attempted: int | None = None, invalid: int = 0) -> SearchSummary:
    return SearchSummary(
        strategy_name="ma_crossover",
        search_parameter_names=["short_window", "long_window"],
        attempted_combinations=attempted if attempted is not None else len(results) + invalid,
        valid_combinations=len(results),
        invalid_combinations=invalid,
        result_count=len(results),
        ranking_score="score",
        best_result=results[0] if results else None,
        top_results=results[:3],
    )


def test_cli_search_exits_with_clear_error_on_invalid_grid(
    sample_market_csv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphaforge",
            "search",
            "--data",
            str(sample_market_csv),
            "--output-dir",
            str(tmp_path),
            "--short-windows",
            "5",
            "6",
            "--long-windows",
            "3",
            "4",
        ],
    )

    with pytest.raises(SystemExit, match="No valid parameter combinations remain after strategy validation"):
        main()


def test_cli_run_exits_with_clear_error_on_invalid_windows(
    sample_market_csv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphaforge",
            "run",
            "--data",
            str(sample_market_csv),
            "--output-dir",
            str(tmp_path),
            "--short-window",
            "5",
            "--long-window",
            "5",
        ],
    )

    with pytest.raises(SystemExit, match="short_window must be smaller than long_window"):
        main()


def test_cli_fetch_twse_does_not_require_run_arguments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "twse.csv"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphaforge",
            "fetch-twse",
            "--stock-no",
            "2330",
            "--start-month",
            "2024-01",
            "--end-month",
            "2024-01",
            "--output",
            str(output_path),
        ],
    )

    request_factory = lambda **kwargs: kwargs
    loader = (
        request_factory,
        lambda request: pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"]),
        lambda frame, path: frame.to_csv(path, index=False) or path,
    )
    with patch("alphaforge.cli._load_twse_client", return_value=loader):
        main()

    assert output_path.exists()


def test_cli_search_prints_summary_payload(
    sample_market_csv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphaforge",
            "search",
            "--data",
            str(sample_market_csv),
            "--output-dir",
            str(tmp_path),
            "--experiment-name",
            "summary_case",
            "--short-windows",
            "2",
            "--long-windows",
            "4",
        ],
    )

    main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["strategy_name"] == "ma_crossover"
    assert payload["search_parameter_names"] == ["short_window", "long_window"]
    assert payload["attempted_combinations"] == 1
    assert payload["valid_combinations"] == 1
    assert payload["invalid_combinations"] == 0
    assert payload["result_count"] == 1
    assert payload["ranking_score"] == "score"
    assert payload["best_result"] is not None
    assert Path(payload["ranked_results_path"]).name == "ranked_results.csv"
    assert Path(payload["ranked_results_path"]).parent.name == "summary_case"
    assert len(payload["top_results"]) == 1
    assert "report_path" not in payload
    assert "search_report_path" not in payload


def test_cli_run_path_does_not_load_twse_client(
    sample_market_csv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphaforge",
            "run",
            "--data",
            str(sample_market_csv),
            "--output-dir",
            str(tmp_path),
            "--short-window",
            "2",
            "--long-window",
            "3",
        ],
    )

    sample_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 3}),
        backtest_config=BacktestConfig(initial_capital=1000.0, fee_rate=0.0, slippage_rate=0.0, annualization_factor=252),
        metrics=MetricReport(
            total_return=0.1,
            annualized_return=0.1,
            sharpe_ratio=1.0,
            max_drawdown=-0.1,
            win_rate=1.0,
            turnover=1.0,
            trade_count=1,
        ),
        score=0.5,
    )

    with patch("alphaforge.cli._load_twse_client", side_effect=AssertionError("TWSE loader should not be used")), patch(
        "alphaforge.cli.run_experiment_with_artifacts",
        return_value=ExperimentExecutionOutput(
            result=sample_result,
            equity_curve=pd.DataFrame(),
            trade_log=pd.DataFrame(),
            report_input=ExperimentReportInput(
                result=sample_result,
                equity_curve=pd.DataFrame(),
                trades=pd.DataFrame(),
                benchmark_summary={"total_return": 0.0, "max_drawdown": 0.0},
                benchmark_curve=pd.DataFrame(),
            ),
            artifact_receipt=None,
        ),
    ):
        main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["strategy_spec"]["parameters"] == {"short_window": 2, "long_window": 3}
    assert "report_path" not in payload
    assert payload["artifacts"] is None


def test_cli_run_generates_report_only_when_requested(
    sample_market_csv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphaforge",
            "run",
            "--data",
            str(sample_market_csv),
            "--output-dir",
            str(tmp_path),
            "--experiment-name",
            "report_case",
            "--short-window",
            "2",
            "--long-window",
            "3",
            "--generate-report",
        ],
    )

    sample_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 3}),
        backtest_config=BacktestConfig(initial_capital=1000.0, fee_rate=0.0, slippage_rate=0.0, annualization_factor=252),
        metrics=MetricReport(
            total_return=0.1,
            annualized_return=0.1,
            sharpe_ratio=1.0,
            max_drawdown=-0.1,
            win_rate=1.0,
            turnover=1.0,
            trade_count=1,
        ),
        score=0.5,
    )
    sample_equity_curve = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=3, freq="D"),
            "equity": [1000.0, 1010.0, 990.0],
        }
    )
    sample_trades = pd.DataFrame()
    sample_receipt = ArtifactReceipt(
        run_dir=tmp_path / "report_case",
        equity_curve_path=tmp_path / "report_case" / "equity_curve.csv",
        trade_log_path=tmp_path / "report_case" / "trade_log.csv",
        metrics_summary_path=tmp_path / "report_case" / "metrics_summary.json",
    )

    with patch(
        "alphaforge.cli.run_experiment_with_artifacts",
        return_value=ExperimentExecutionOutput(
            result=sample_result,
            equity_curve=sample_equity_curve,
            trade_log=sample_trades,
            report_input=ExperimentReportInput(
                result=sample_result,
                equity_curve=sample_equity_curve,
                trades=sample_trades,
                benchmark_summary={"total_return": 0.0, "max_drawdown": 0.0},
                benchmark_curve=sample_equity_curve,
            ),
            artifact_receipt=sample_receipt,
        ),
    ), patch(
        "alphaforge.cli.render_experiment_report", return_value="<html>report</html>"
    ), patch("alphaforge.cli.save_experiment_report", side_effect=lambda content, path: path):
        main()

    payload = json.loads(capsys.readouterr().out)
    report_path = Path(payload["report_path"])
    assert report_path.name == "report.html"
    assert report_path.parent.name == "report_case"
    assert Path(payload["artifacts"]["equity_curve_path"]).name == "equity_curve.csv"


def test_cli_twse_search_fetches_saves_and_runs_search(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data_output = tmp_path / "twse_2330.csv"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphaforge",
            "twse-search",
            "--stock-no",
            "2330",
            "--start-month",
            "2024-01",
            "--end-month",
            "2024-01",
            "--data-output",
            str(data_output),
            "--output-dir",
            str(tmp_path),
            "--experiment-name",
            "twse_summary_case",
            "--short-windows",
            "2",
            "--long-windows",
            "4",
        ],
    )

    sample_frame = pd.DataFrame(
        [{"datetime": "2024-01-02", "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 100.0}]
    )
    sample_result = ExperimentResult(
        data_spec=DataSpec(path=data_output, symbol="2330"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(initial_capital=1000.0, fee_rate=0.0, slippage_rate=0.0, annualization_factor=252),
        metrics=MetricReport(
            total_return=0.1,
            annualized_return=0.1,
            sharpe_ratio=1.0,
            max_drawdown=-0.1,
            win_rate=1.0,
            turnover=1.0,
            trade_count=1,
        ),
        score=0.5,
    )

    request_factory = lambda **kwargs: kwargs
    loader = (
        request_factory,
        lambda request: sample_frame,
        lambda frame, path: frame.to_csv(path, index=False) or path,
    )
    with patch("alphaforge.cli._load_twse_client", return_value=loader), patch(
        "alphaforge.cli.run_search_with_details",
        return_value=SearchExecutionOutput(
            ranked_results=[sample_result],
            summary=_make_search_summary([sample_result]),
            artifact_receipt=SearchArtifactReceipt(
                search_root=tmp_path / "twse_summary_case",
                ranked_results_path=tmp_path / "twse_summary_case" / "ranked_results.csv",
            ),
        ),
    ):
        main()

    payload = json.loads(capsys.readouterr().out)
    assert data_output.exists()
    assert payload["result_count"] == 1
    assert Path(payload["data_output"]).name == "twse_2330.csv"
    assert payload["best_result"]["strategy_spec"]["parameters"] == {"short_window": 2, "long_window": 4}


def test_cli_search_generates_only_best_report_when_requested(
    sample_market_csv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphaforge",
            "search",
            "--data",
            str(sample_market_csv),
            "--output-dir",
            str(tmp_path),
            "--experiment-name",
            "search_report_case",
            "--short-windows",
            "2",
            "--long-windows",
            "4",
            "--generate-report",
        ],
    )

    sample_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(initial_capital=1000.0, fee_rate=0.0, slippage_rate=0.0, annualization_factor=252),
        metrics=MetricReport(
            total_return=0.1,
            annualized_return=0.1,
            sharpe_ratio=1.0,
            max_drawdown=-0.1,
            win_rate=1.0,
            turnover=1.0,
            trade_count=1,
        ),
        score=0.5,
    )

    with patch(
        "alphaforge.cli.run_search_with_details",
        return_value=SearchExecutionOutput(
            ranked_results=[sample_result],
            summary=_make_search_summary([sample_result]),
            artifact_receipt=SearchArtifactReceipt(
                search_root=tmp_path / "search_report_case",
                ranked_results_path=tmp_path / "search_report_case" / "ranked_results.csv",
                best_report_path=tmp_path / "search_report_case" / "best_report.html",
                comparison_report_path=tmp_path / "search_report_case" / "search_report.html",
            ),
        ),
    ) as run_search_mock:
        main()

    payload = json.loads(capsys.readouterr().out)
    assert run_search_mock.call_args.kwargs["generate_best_report"] is True
    assert Path(payload["report_path"]).name == "best_report.html"
    assert Path(payload["report_path"]).parent.name == "search_report_case"
    assert Path(payload["search_report_path"]).name == "search_report.html"
    assert Path(payload["search_report_path"]).parent.name == "search_report_case"


def test_cli_search_with_empty_ranked_results_still_returns_search_report_path(
    sample_market_csv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphaforge",
            "search",
            "--data",
            str(sample_market_csv),
            "--output-dir",
            str(tmp_path),
            "--experiment-name",
            "empty_search_case",
            "--short-windows",
            "2",
            "--long-windows",
            "4",
            "--generate-report",
        ],
    )

    with patch(
        "alphaforge.cli.run_search_with_details",
        return_value=SearchExecutionOutput(
            ranked_results=[],
            summary=_make_search_summary([]),
            artifact_receipt=SearchArtifactReceipt(
                search_root=tmp_path / "empty_search_case",
                comparison_report_path=tmp_path / "empty_search_case" / "search_report.html",
            ),
        ),
    ):
        main()

    payload = json.loads(capsys.readouterr().out)
    assert "report_path" not in payload
    assert Path(payload["search_report_path"]).name == "search_report.html"


def test_cli_search_omits_missing_artifact_paths_instead_of_guessing(
    sample_market_csv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphaforge",
            "search",
            "--data",
            str(sample_market_csv),
            "--output-dir",
            str(tmp_path),
            "--experiment-name",
            "partial_search_case",
            "--short-windows",
            "2",
            "--long-windows",
            "4",
            "--generate-report",
        ],
    )

    sample_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(initial_capital=1000.0, fee_rate=0.0, slippage_rate=0.0, annualization_factor=252),
        metrics=MetricReport(
            total_return=0.1,
            annualized_return=0.1,
            sharpe_ratio=1.0,
            max_drawdown=-0.1,
            win_rate=1.0,
            turnover=1.0,
            trade_count=1,
        ),
        score=0.5,
    )

    with patch(
        "alphaforge.cli.run_search_with_details",
        return_value=SearchExecutionOutput(
            ranked_results=[sample_result],
            summary=_make_search_summary([sample_result]),
            artifact_receipt=SearchArtifactReceipt(
                search_root=tmp_path / "partial_search_case",
                ranked_results_path=tmp_path / "partial_search_case" / "ranked_results.csv",
                comparison_report_path=tmp_path / "partial_search_case" / "search_report.html",
            ),
        ),
    ):
        main()

    payload = json.loads(capsys.readouterr().out)
    assert Path(payload["ranked_results_path"]).name == "ranked_results.csv"
    assert "report_path" not in payload
    assert Path(payload["search_report_path"]).name == "search_report.html"
