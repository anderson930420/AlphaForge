from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from alphaforge.cli import main
from alphaforge.experiment_runner import (
    ExperimentExecutionOutput,
    SearchExecutionOutput,
    ValidationExecutionOutput,
    run_validate_search,
    run_walk_forward_search,
)
from alphaforge.report import ExperimentReportInput
from alphaforge.schemas import BacktestConfig, DataSpec, ExperimentResult, MetricReport, StrategySpec
from alphaforge.storage import serialize_walk_forward_result


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
    train_ranked_path = tmp_path / "validation_case" / "train_ranked_results.csv"
    train_best_metrics_path = tmp_path / "validation_case" / "train_best" / "metrics_summary.json"
    test_metrics_path = tmp_path / "validation_case" / "test_selected" / "metrics_summary.json"

    assert summary_path.exists()
    assert train_ranked_path.exists()
    assert train_best_metrics_path.exists()
    assert test_metrics_path.exists()
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert "validation_summary_path" not in summary_payload
    assert Path(summary_payload["train_ranked_results_path"]).name == "train_ranked_results.csv"
    assert "test_benchmark_summary" in summary_payload
    assert "total_return" in summary_payload["test_benchmark_summary"]
    assert "max_drawdown" in summary_payload["test_benchmark_summary"]
    assert not hasattr(result, "validation_summary_path")
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
        "alphaforge.experiment_runner._run_search_on_market_data",
        return_value=SearchExecutionOutput(ranked_results=[train_best]),
    ) as run_search_mock, patch(
        "alphaforge.experiment_runner._run_experiment_on_market_data",
        return_value=ExperimentExecutionOutput(
            result=test_result,
            equity_curve=pd.DataFrame(),
            trade_log=pd.DataFrame(),
            report_input=ExperimentReportInput(
                result=test_result,
                equity_curve=pd.DataFrame(),
                trades=pd.DataFrame(),
                benchmark_summary={"total_return": 0.0, "max_drawdown": 0.0},
                benchmark_curve=pd.DataFrame(),
            ),
            artifact_receipt=None,
        ),
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
    assert result.test_benchmark_summary == {"total_return": 0.0, "max_drawdown": 0.0}


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
        "train_ranked_results_path": str(tmp_path / "validation_case" / "train_ranked_results.csv"),
    }

    with patch(
        "alphaforge.cli.run_validate_search_with_details",
        return_value=ValidationExecutionOutput(
            validation_result=run_validate_search(
                data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
                parameter_grid={"short_window": [2], "long_window": [3]},
                split_ratio=0.5,
                output_dir=tmp_path,
                experiment_name="validation_case",
            ),
            validation_summary_path=tmp_path / "validation_case" / "validation_summary.json",
        ),
    ) as run_validate_mock, patch(
        "alphaforge.cli.serialize_validation_result", return_value=validation_payload
    ):
        main()

    payload = json.loads(capsys.readouterr().out)
    assert run_validate_mock.call_args.kwargs["split_ratio"] == 0.5
    assert payload["selected_strategy_spec"]["parameters"] == {"short_window": 2, "long_window": 3}
    assert Path(payload["train_ranked_results_path"]).name == "train_ranked_results.csv"
    assert Path(payload["validation_summary_path"]).name == "validation_summary.json"


def test_run_walk_forward_search_creates_chronological_fold_outputs(sample_market_csv: Path, tmp_path: Path) -> None:
    result = run_walk_forward_search(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"short_window": [2], "long_window": [3]},
        train_size=4,
        test_size=2,
        step_size=2,
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="walk_forward_case",
    )

    summary_path = tmp_path / "walk_forward_case" / "walk_forward_summary.json"
    fold_results_path = tmp_path / "walk_forward_case" / "fold_results.csv"
    fold_root = tmp_path / "walk_forward_case" / "folds" / "fold_001"

    assert result.walk_forward_summary_path == summary_path
    assert result.fold_results_path == fold_results_path
    assert summary_path.exists()
    assert fold_results_path.exists()
    assert len(result.folds) == 2
    assert result.folds[0].train_end < result.folds[0].test_start
    assert "total_return" in result.folds[0].test_benchmark_summary
    assert "mean_benchmark_total_return" in result.aggregate_benchmark_metrics
    assert (fold_root / "train_search" / "ranked_results.csv").exists()
    assert (fold_root / "test_selected" / "metrics_summary.json").exists()
    fold_results_frame = pd.read_csv(fold_results_path)
    assert fold_results_frame.loc[0, "fold_path"] == str(fold_root)
    assert not hasattr(result.folds[0], "fold_path")


def test_run_walk_forward_search_uses_train_fold_for_search_and_next_window_for_test(sample_market_csv: Path) -> None:
    train_best_fold_1 = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 1),
        score=0.9,
    )
    train_best_fold_2 = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 3, "long_window": 4}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.08, 0.08, 0.8, -0.09, 0.5, 0.8, 1),
        score=0.7,
    )
    test_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=train_best_fold_1.strategy_spec,
        backtest_config=train_best_fold_1.backtest_config,
        metrics=MetricReport(0.03, 0.03, 0.5, -0.05, 0.5, 0.6, 1),
        score=0.2,
    )
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=10, freq="D"),
            "open": range(10),
            "high": range(10),
            "low": range(10),
            "close": range(10),
            "volume": [1.0] * 10,
        }
    )

    with patch("alphaforge.experiment_runner.load_market_data", return_value=market_data), patch(
        "alphaforge.experiment_runner._run_search_on_market_data",
        side_effect=[
            SearchExecutionOutput(ranked_results=[train_best_fold_1]),
            SearchExecutionOutput(ranked_results=[train_best_fold_2]),
            SearchExecutionOutput(ranked_results=[train_best_fold_2]),
        ],
    ) as run_search_mock, patch(
        "alphaforge.experiment_runner._run_experiment_on_market_data",
        return_value=ExperimentExecutionOutput(
            result=test_result,
            equity_curve=pd.DataFrame(),
            trade_log=pd.DataFrame(),
            report_input=ExperimentReportInput(
                result=test_result,
                equity_curve=pd.DataFrame(),
                trades=pd.DataFrame(),
                benchmark_summary={"total_return": 0.0, "max_drawdown": 0.0},
                benchmark_curve=pd.DataFrame(),
            ),
            artifact_receipt=None,
        ),
    ) as run_experiment_mock:
        result = run_walk_forward_search(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid={"short_window": [2, 3], "long_window": [4]},
            train_size=4,
            test_size=2,
            step_size=2,
        )

    first_train = run_search_mock.call_args_list[0].kwargs["market_data"]
    first_test = run_experiment_mock.call_args_list[0].kwargs["market_data"]
    second_selected_strategy = run_experiment_mock.call_args_list[1].kwargs["strategy_spec"]

    assert first_train["datetime"].max() < first_test["datetime"].min()
    assert second_selected_strategy.parameters == {"short_window": 3, "long_window": 4}
    assert len(result.folds) == 3


def test_storage_serializes_walk_forward_runtime_result_without_fold_path_residue(sample_market_csv: Path) -> None:
    result = run_walk_forward_search(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"short_window": [2], "long_window": [3]},
        train_size=4,
        test_size=2,
        step_size=2,
    )

    payload = serialize_walk_forward_result(result)

    assert "fold_path" not in payload["folds"][0]


def test_run_walk_forward_search_rejects_dataset_too_short(sample_market_csv: Path) -> None:
    with pytest.raises(ValueError, match="Dataset is too short"):
        run_walk_forward_search(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid={"short_window": [2], "long_window": [3]},
            train_size=7,
            test_size=3,
            step_size=1,
        )


def test_run_walk_forward_search_rejects_non_positive_window_sizes(sample_market_csv: Path) -> None:
    with pytest.raises(ValueError, match="must be positive integers"):
        run_walk_forward_search(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid={"short_window": [2], "long_window": [3]},
            train_size=4,
            test_size=2,
            step_size=0,
        )


def test_cli_walk_forward_prints_summary_payload(
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
            "walk-forward",
            "--data",
            str(sample_market_csv),
            "--output-dir",
            str(tmp_path),
            "--experiment-name",
            "walk_forward_case",
            "--short-windows",
            "2",
            "--long-windows",
            "3",
            "--train-size",
            "4",
            "--test-size",
            "2",
            "--step-size",
            "2",
        ],
    )

    walk_forward_payload = {
        "walk_forward_config": {"train_size": 4, "test_size": 2, "step_size": 2},
        "aggregate_test_metrics": {"fold_count": 2},
        "aggregate_benchmark_metrics": {"fold_count": 2, "mean_benchmark_total_return": 0.03},
        "walk_forward_summary_path": str(tmp_path / "walk_forward_case" / "walk_forward_summary.json"),
    }

    with patch("alphaforge.cli.run_walk_forward_search") as run_walk_forward_mock, patch(
        "alphaforge.cli.serialize_walk_forward_result", return_value=walk_forward_payload
    ):
        main()

    payload = json.loads(capsys.readouterr().out)
    assert run_walk_forward_mock.call_args.kwargs["train_size"] == 4
    assert payload["walk_forward_config"]["step_size"] == 2
    assert payload["aggregate_benchmark_metrics"]["mean_benchmark_total_return"] == 0.03
    assert Path(payload["walk_forward_summary_path"]).name == "walk_forward_summary.json"
