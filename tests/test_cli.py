from __future__ import annotations

import sys
import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from alphaforge.cli import main
from alphaforge.schemas import BacktestConfig, DataSpec, ExperimentResult, MetricReport, StrategySpec


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

    assert payload["result_count"] == 1
    assert payload["best_result"] is not None
    assert Path(payload["ranked_results_path"]).name == "ranked_results.csv"
    assert Path(payload["ranked_results_path"]).parent.name == "summary_case"
    assert len(payload["top_results"]) == 1


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
        "alphaforge.cli.run_experiment", return_value=(sample_result, pd.DataFrame(), pd.DataFrame())
    ):
        main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["strategy_spec"]["parameters"] == {"short_window": 2, "long_window": 3}


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
    with patch("alphaforge.cli._load_twse_client", return_value=loader), patch("alphaforge.cli.run_search", return_value=[sample_result]):
        main()

    payload = json.loads(capsys.readouterr().out)
    assert data_output.exists()
    assert payload["result_count"] == 1
    assert Path(payload["data_output"]).name == "twse_2330.csv"
    assert payload["best_result"]["strategy_spec"]["parameters"] == {"short_window": 2, "long_window": 4}
