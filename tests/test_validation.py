from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from alphaforge.cli import main
from alphaforge.experiment_runner import run_validate_search
from alphaforge.schemas import BacktestConfig, DataSpec, ExperimentResult, MetricReport, StrategySpec


def test_run_validate_search_splits_data_chronologically_and_saves_outputs(sample_market_csv: Path, tmp_path: Path) -> None:
    result = run_validate_search(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"short_window": [2], "long_window": [3]},
        split_ratio=0.5,
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="validation_case",
    )

    summary_path = tmp_path / "validation_case" / "validation_summary.json"
    train_ranked_path = tmp_path / "validation_case" / "train_search" / "ranked_results.csv"
    test_metrics_path = tmp_path / "validation_case" / "test_selected" / "metrics_summary.json"

    assert result.validation_summary_path == summary_path
    assert summary_path.exists()
    assert train_ranked_path.exists()
    assert test_metrics_path.exists()
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert Path(summary_payload["validation_summary_path"]).name == "validation_summary.json"
    assert result.metadata["train_rows"] == 4
    assert result.metadata["test_rows"] == 4
    assert result.metadata["train_end"] < result.metadata["test_start"]


def test_run_validate_search_uses_train_only_for_search_and_selected_params_for_test(sample_market_csv: Path) -> None:
    train_best = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 1),
        score=0.9,
    )
    test_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=train_best.strategy_spec,
        backtest_config=train_best.backtest_config,
        metrics=MetricReport(0.05, 0.05, 0.8, -0.08, 0.5, 0.7, 1),
        score=0.4,
    )
    train_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=4, freq="D"),
            "open": [1.0, 2.0, 3.0, 4.0],
            "high": [1.0, 2.0, 3.0, 4.0],
            "low": [1.0, 2.0, 3.0, 4.0],
            "close": [1.0, 2.0, 3.0, 4.0],
            "volume": [1.0, 1.0, 1.0, 1.0],
        }
    )
    test_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-05", periods=4, freq="D"),
            "open": [5.0, 6.0, 7.0, 8.0],
            "high": [5.0, 6.0, 7.0, 8.0],
            "low": [5.0, 6.0, 7.0, 8.0],
            "close": [5.0, 6.0, 7.0, 8.0],
            "volume": [1.0, 1.0, 1.0, 1.0],
        }
    )

    with patch("alphaforge.experiment_runner.load_market_data", return_value=pd.concat([train_data, test_data], ignore_index=True)), patch(
        "alphaforge.experiment_runner._run_search_on_market_data", return_value=[train_best]
    ) as run_search_mock, patch(
        "alphaforge.experiment_runner._run_experiment_on_market_data", return_value=(test_result, pd.DataFrame(), pd.DataFrame())
    ) as run_experiment_mock:
        result = run_validate_search(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid={"short_window": [2], "long_window": [4]},
            split_ratio=0.5,
        )

    searched_train = run_search_mock.call_args.kwargs["market_data"]
    tested_strategy = run_experiment_mock.call_args.kwargs["strategy_spec"]
    tested_market = run_experiment_mock.call_args.kwargs["market_data"]

    assert searched_train["datetime"].max() < tested_market["datetime"].min()
    assert tested_strategy.parameters == {"short_window": 2, "long_window": 4}
    assert result.selected_strategy_spec.parameters == {"short_window": 2, "long_window": 4}


def test_run_validate_search_rejects_invalid_split_ratio(sample_market_csv: Path) -> None:
    with pytest.raises(ValueError, match="split_ratio"):
        run_validate_search(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid={"short_window": [2], "long_window": [3]},
            split_ratio=1.0,
        )


def test_run_validate_search_rejects_train_segment_too_short_for_windows(sample_market_csv: Path) -> None:
    with pytest.raises(ValueError, match="Train segment is too short"):
        run_validate_search(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid={"short_window": [2], "long_window": [6]},
            split_ratio=0.5,
        )


def test_cli_validate_search_prints_validation_summary_payload(
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
            "validate-search",
            "--data",
            str(sample_market_csv),
            "--output-dir",
            str(tmp_path),
            "--experiment-name",
            "validation_case",
            "--short-windows",
            "2",
            "--long-windows",
            "3",
            "--split-ratio",
            "0.5",
        ],
    )

    validation_payload = {
        "split_config": {"split_ratio": 0.5},
        "selected_strategy_spec": {"name": "ma_crossover", "parameters": {"short_window": 2, "long_window": 3}},
        "train_best_result": {"score": 0.8},
        "test_result": {"score": 0.4},
        "validation_summary_path": str(tmp_path / "validation_case" / "validation_summary.json"),
    }

    with patch("alphaforge.cli.run_validate_search") as run_validate_mock:
        run_validate_mock.return_value.to_dict.return_value = validation_payload
        main()

    payload = json.loads(capsys.readouterr().out)
    assert run_validate_mock.call_args.kwargs["split_ratio"] == 0.5
    assert payload["selected_strategy_spec"]["parameters"] == {"short_window": 2, "long_window": 3}
    assert Path(payload["validation_summary_path"]).name == "validation_summary.json"
