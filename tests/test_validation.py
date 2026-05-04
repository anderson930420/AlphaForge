from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from alphaforge.cli import main
from alphaforge.policy_types import ParameterGrid
from alphaforge.experiment_runner import (
    ExperimentExecutionOutput,
    SearchExecutionOutput,
    ValidationExecutionOutput,
    WalkForwardExecutionOutput,
    run_validate_search,
    run_walk_forward_search,
    run_walk_forward_search_with_details,
)
from alphaforge.research_policy import ResearchPolicyConfig
from alphaforge.report import ExperimentReportInput
from alphaforge.schemas import (
    BacktestConfig,
    DataSpec,
    ExperimentResult,
    MetricReport,
    PermutationTestArtifactReceipt,
    PermutationTestExecutionOutput,
    PermutationTestSummary,
    SearchSummary,
    StrategySpec,
    ValidationPermutationConfig,
)
from alphaforge.storage import (
    ValidationArtifactReceipt,
    WalkForwardArtifactReceipt,
    serialize_walk_forward_artifact_receipt,
    serialize_walk_forward_result,
)


def _make_search_summary(results: list[ExperimentResult]) -> SearchSummary:
    return SearchSummary(
        strategy_name="ma_crossover",
        search_parameter_names=["short_window", "long_window"],
        attempted_combinations=len(results),
        valid_combinations=len(results),
        invalid_combinations=0,
        result_count=len(results),
        ranking_score="score",
        best_result=results[0] if results else None,
        top_results=results[:3],
    )


def _make_validation_permutation_summary(
    *,
    strategy_spec: StrategySpec,
    empirical_p_value: float | None,
    permutation_scope: str = "test",
) -> PermutationTestSummary:
    return PermutationTestSummary(
        strategy_name=strategy_spec.name,
        strategy_parameters=dict(strategy_spec.parameters),
        target_metric_name="score",
        permutation_mode="block",
        block_size=2,
        real_observed_metric_value=0.25,
        permutation_metric_values=[0.1, 0.2, 0.3],
        permutation_count=3,
        seed=7,
        null_ge_count=1,
        empirical_p_value=empirical_p_value,
        null_model="return_block_reconstruction",
        metadata={"permutation_scope": permutation_scope},
    )


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
    assert summary_payload["validation_summary_path"] == str(summary_path)
    assert Path(summary_payload["train_ranked_results_path"]).name == "train_ranked_results.csv"
    assert "test_benchmark_summary" in summary_payload
    assert "total_return" in summary_payload["test_benchmark_summary"]
    assert "max_drawdown" in summary_payload["test_benchmark_summary"]
    assert summary_payload["candidate_decision"]["verdict"] == summary_payload["candidate_evidence"]["verdict"]
    assert summary_payload["candidate_decision"]["decision_reasons"]
    assert summary_payload["policy_decision_path"].endswith("policy_decision.json")
    assert summary_payload["candidate_evidence"]["degradation_summary"]["return_degradation"] == result.candidate_evidence.degradation_summary["return_degradation"]
    assert result.candidate_evidence.search_rank == 1
    assert result.candidate_evidence.search_result_count == 1
    assert result.candidate_decision is not None
    assert result.candidate_decision.verdict == result.candidate_evidence.verdict
    assert result.candidate_decision.policy_scope == "validate-search"
    assert result.research_policy_decision is not None
    assert result.research_policy_decision.verdict == "promote"
    assert result.research_policy_decision.reasons
    assert result.research_policy_decision.checks
    assert result.research_policy_config["required_permutation_null_model"] is None
    assert result.permutation_config is not None
    assert result.permutation_config.enabled is False
    assert result.candidate_evidence.permutation_summary is None
    assert result.candidate_evidence.permutation_status == "skipped"
    assert result.candidate_evidence.bootstrap_evidence is not None
    assert result.candidate_evidence.bootstrap_evidence.n_bootstrap == 1000
    assert result.candidate_evidence.bootstrap_evidence.seed == 42
    assert result.candidate_evidence.cost_sensitivity is not None
    assert result.candidate_evidence.cost_sensitivity.verdict in {"stable", "cost_fragile"}
    assert result.test_result.metadata["bootstrap_evidence"]["seed"] == 42
    assert result.test_result.metadata["cost_sensitivity"]["verdict"] in {"stable", "cost_fragile"}
    assert "low_cost" in summary_payload["candidate_evidence"]["cost_sensitivity"]
    assert "base_cost" in summary_payload["candidate_evidence"]["cost_sensitivity"]
    assert "high_cost" in summary_payload["candidate_evidence"]["cost_sensitivity"]
    assert summary_payload["permutation_config"]["enabled"] is False
    assert summary_payload["candidate_evidence"]["permutation_status"] == "skipped"
    assert summary_payload["candidate_evidence"]["bootstrap_evidence"]["n_bootstrap"] == 1000
    assert summary_payload["candidate_evidence"]["bootstrap_evidence"]["seed"] == 42
    assert summary_payload["candidate_evidence"]["cost_sensitivity"]["verdict"] in {"stable", "cost_fragile"}
    assert summary_payload["test_result"]["metadata"]["bootstrap_evidence"]["seed"] == 42
    assert summary_payload["test_result"]["metadata"]["cost_sensitivity"]["verdict"] in {"stable", "cost_fragile"}
    assert (
        result.candidate_evidence.degradation_summary["return_degradation"]
        == result.test_result.metrics.annualized_return - result.train_best_result.metrics.annualized_return
    )
    assert result.candidate_evidence.benchmark_relative_summary["benchmark_total_return"] == summary_payload["candidate_evidence"]["benchmark_relative_summary"]["benchmark_total_return"]
    assert not hasattr(result, "validation_summary_path")
    assert not hasattr(result, "train_ranked_results_path")
    assert result.metadata["train_rows"] == 4
    assert result.metadata["test_rows"] == 4
    assert result.metadata["train_end"] < result.metadata["test_start"]


def test_run_validate_search_uses_train_only_for_search_and_selected_params_for_test(sample_market_csv: Path) -> None:
    train_best = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 1, "long_window": 2}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 1, bar_count=1),
        score=0.9,
    )
    test_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=train_best.strategy_spec,
        backtest_config=train_best.backtest_config,
        metrics=MetricReport(0.05, 0.05, 0.8, -0.08, 0.5, 0.7, 1, bar_count=1),
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

    with patch("alphaforge.runner_workflows.load_market_data", return_value=pd.concat([train_data, test_data], ignore_index=True)), patch(
        "alphaforge.runner_workflows.run_search_on_market_data",
        return_value=SearchExecutionOutput(ranked_results=[train_best], summary=_make_search_summary([train_best])),
    ) as run_search_mock, patch(
        "alphaforge.runner_workflows.run_experiment_on_market_data",
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
    assert tested_strategy.parameters == {"short_window": 1, "long_window": 2}
    assert result.selected_strategy_spec.parameters == {"short_window": 1, "long_window": 2}
    assert result.test_benchmark_summary == {"total_return": 0.0, "max_drawdown": 0.0}
    assert result.candidate_decision is not None
    assert result.candidate_evidence.verdict == result.candidate_decision.verdict
    assert result.candidate_decision.verdict == result.candidate_evidence.verdict
    assert result.candidate_decision.policy_scope == "validate-search"
    assert result.candidate_evidence.search_rank == 1
    assert result.candidate_evidence.search_result_count == 1


@pytest.mark.parametrize(
    "strategy_name,parameter_grid,selected_parameters",
    [
        ("ma_crossover", {"short_window": [2], "long_window": [4]}, {"short_window": 2, "long_window": 4}),
        ("breakout", {"lookback_window": [3]}, {"lookback_window": 3}),
    ],
)
def test_run_validate_search_runs_permutation_diagnostic_for_selected_candidate(
    sample_market_csv: Path,
    strategy_name: str,
    parameter_grid: ParameterGrid,
    selected_parameters: dict[str, int],
) -> None:
    train_best = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name=strategy_name, parameters=selected_parameters),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 2, bar_count=1),
        score=0.9,
    )
    test_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=train_best.strategy_spec,
        backtest_config=train_best.backtest_config,
        metrics=MetricReport(0.05, 0.12, 0.8, -0.08, 0.5, 0.7, 2, bar_count=1),
        score=0.4,
    )
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=8, freq="D"),
            "open": range(1, 9),
            "high": range(1, 9),
            "low": range(1, 9),
            "close": range(1, 9),
            "volume": [1.0] * 8,
        }
    )
    permutation_summary = _make_validation_permutation_summary(
        strategy_spec=train_best.strategy_spec,
        empirical_p_value=0.04,
    )
    permutation_receipt = PermutationTestArtifactReceipt(
        permutation_test_summary_path=Path("/tmp/permutation_test_summary.json"),
        permutation_scores_path=Path("/tmp/permutation_scores.csv"),
    )

    with patch("alphaforge.runner_workflows.load_market_data", return_value=market_data), patch(
        "alphaforge.runner_workflows.run_search_on_market_data",
        return_value=SearchExecutionOutput(ranked_results=[train_best], summary=_make_search_summary([train_best])),
    ), patch(
        "alphaforge.runner_workflows.run_experiment_on_market_data",
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
    ), patch(
        "alphaforge.runner_workflows.run_permutation_test_with_details",
        return_value=PermutationTestExecutionOutput(
            permutation_test_summary=permutation_summary,
            artifact_receipt=permutation_receipt,
        ),
    ) as run_permutation_mock:
        result = run_validate_search(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid=parameter_grid,
            split_ratio=0.5,
            permutation_config=ValidationPermutationConfig(enabled=True, permutations=3, seed=7, block_size=2),
        )

    permutation_call = run_permutation_mock.call_args.kwargs
    expected_test_data = market_data.iloc[4:].reset_index(drop=True)
    assert permutation_call["strategy_spec"].parameters == selected_parameters
    assert permutation_call["market_data"].reset_index(drop=True).equals(expected_test_data)
    assert permutation_call["permutation_scope"] == "test"
    assert result.candidate_evidence.permutation_summary is not None
    assert result.candidate_evidence.permutation_summary.strategy_parameters == selected_parameters
    assert result.candidate_evidence.permutation_status == "completed_passed"
    assert result.research_policy_decision is not None
    assert result.research_policy_decision.verdict == "promote"
    assert result.research_policy_decision.checks["max_permutation_p_value"] is True


def test_run_validate_search_marks_completed_failed_when_permutation_p_value_is_above_default_threshold(
    sample_market_csv: Path,
) -> None:
    train_best = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 2, bar_count=1),
        score=0.9,
    )
    test_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=train_best.strategy_spec,
        backtest_config=train_best.backtest_config,
        metrics=MetricReport(0.05, 0.12, 0.8, -0.08, 0.5, 0.7, 2, bar_count=1),
        score=0.4,
    )
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=8, freq="D"),
            "open": range(1, 9),
            "high": range(1, 9),
            "low": range(1, 9),
            "close": range(1, 9),
            "volume": [1.0] * 8,
        }
    )

    with patch("alphaforge.runner_workflows.load_market_data", return_value=market_data), patch(
        "alphaforge.runner_workflows.run_search_on_market_data",
        return_value=SearchExecutionOutput(ranked_results=[train_best], summary=_make_search_summary([train_best])),
    ), patch(
        "alphaforge.runner_workflows.run_experiment_on_market_data",
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
    ), patch(
        "alphaforge.runner_workflows.run_permutation_test_with_details",
        return_value=PermutationTestExecutionOutput(
            permutation_test_summary=_make_validation_permutation_summary(
                strategy_spec=train_best.strategy_spec,
                empirical_p_value=0.2,
            ),
            artifact_receipt=PermutationTestArtifactReceipt(
                permutation_test_summary_path=Path("/tmp/permutation_test_summary.json"),
                permutation_scores_path=Path("/tmp/permutation_scores.csv"),
            ),
        ),
    ):
        result = run_validate_search(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid={"short_window": [2], "long_window": [4]},
            split_ratio=0.5,
            permutation_config=ValidationPermutationConfig(enabled=True, permutations=3, seed=7, block_size=2),
        )

    assert result.candidate_evidence.permutation_status == "completed_failed"
    assert result.research_policy_decision is not None
    assert result.research_policy_decision.verdict == "reject"
    assert result.research_policy_decision.checks["max_permutation_p_value"] is False


def test_run_validate_search_marks_error_when_permutation_execution_fails(sample_market_csv: Path) -> None:
    train_best = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 2, bar_count=1),
        score=0.9,
    )
    test_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=train_best.strategy_spec,
        backtest_config=train_best.backtest_config,
        metrics=MetricReport(0.05, 0.12, 0.8, -0.08, 0.5, 0.7, 2, bar_count=1),
        score=0.4,
    )
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=8, freq="D"),
            "open": range(1, 9),
            "high": range(1, 9),
            "low": range(1, 9),
            "close": range(1, 9),
            "volume": [1.0] * 8,
        }
    )

    with patch("alphaforge.runner_workflows.load_market_data", return_value=market_data), patch(
        "alphaforge.runner_workflows.run_search_on_market_data",
        return_value=SearchExecutionOutput(ranked_results=[train_best], summary=_make_search_summary([train_best])),
    ), patch(
        "alphaforge.runner_workflows.run_experiment_on_market_data",
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
    ), patch(
        "alphaforge.runner_workflows.run_permutation_test_with_details",
        side_effect=RuntimeError("boom"),
    ):
        result = run_validate_search(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid={"short_window": [2], "long_window": [4]},
            split_ratio=0.5,
            permutation_config=ValidationPermutationConfig(enabled=True, permutations=3, seed=7, block_size=2),
        )

    assert result.candidate_evidence.permutation_status == "error"
    assert result.candidate_evidence.permutation_summary is None
    assert result.research_policy_decision is not None
    assert result.research_policy_decision.verdict == "reject"


def test_run_validate_search_with_research_policy_threshold_rejects_weak_trade_count(
    sample_market_csv: Path,
) -> None:
    train_best = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 1, bar_count=1),
        score=0.9,
    )
    test_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=train_best.strategy_spec,
        backtest_config=train_best.backtest_config,
        metrics=MetricReport(0.05, 0.05, 0.8, -0.08, 0.5, 0.7, 1, bar_count=1),
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

    with patch("alphaforge.runner_workflows.load_market_data", return_value=pd.concat([train_data, test_data], ignore_index=True)), patch(
        "alphaforge.runner_workflows.run_search_on_market_data",
        return_value=SearchExecutionOutput(ranked_results=[train_best], summary=_make_search_summary([train_best])),
    ), patch(
        "alphaforge.runner_workflows.run_experiment_on_market_data",
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
    ):
        result = run_validate_search(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid={"short_window": [2], "long_window": [4]},
            split_ratio=0.5,
            policy_config=ResearchPolicyConfig(
                min_trade_count=2,
                required_permutation_null_model=None,
                max_permutation_p_value=None,
                required_permutation_scope=None,
            ),
        )

    assert result.research_policy_decision is not None
    assert result.research_policy_decision.verdict == "reject"
    assert result.research_policy_decision.checks["min_trade_count"] is False
    assert any("trade_count 1 below minimum 2" in reason for reason in result.research_policy_decision.reasons)


def test_run_validate_search_with_holdout_cutoff_uses_development_rows_only(sample_market_csv: Path) -> None:
    train_best = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 1, bar_count=1),
        score=0.9,
    )
    test_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=train_best.strategy_spec,
        backtest_config=train_best.backtest_config,
        metrics=MetricReport(0.05, 0.05, 0.8, -0.08, 0.5, 0.7, 1, bar_count=1),
        score=0.4,
    )
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=8, freq="D"),
            "open": [1.0, 2.0, 3.0, 4.0, 100.0, 101.0, 102.0, 103.0],
            "high": [1.0, 2.0, 3.0, 4.0, 100.0, 101.0, 102.0, 103.0],
            "low": [1.0, 2.0, 3.0, 4.0, 100.0, 101.0, 102.0, 103.0],
            "close": [1.0, 2.0, 3.0, 4.0, 100.0, 101.0, 102.0, 103.0],
            "volume": [1.0] * 8,
        }
    )
    dev_cutoff = pd.Timestamp("2024-01-05")
    train_data = market_data.iloc[:4].reset_index(drop=True)
    test_data = market_data.iloc[4:8].reset_index(drop=True)

    with patch("alphaforge.runner_workflows.load_market_data", return_value=market_data), patch(
        "alphaforge.runner_workflows.run_search_on_market_data",
        return_value=SearchExecutionOutput(ranked_results=[train_best], summary=_make_search_summary([train_best])),
    ) as run_search_mock, patch(
        "alphaforge.runner_workflows.run_experiment_on_market_data",
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
            parameter_grid={"short_window": [1], "long_window": [2]},
            split_ratio=0.5,
            holdout_cutoff_date="2024-01-05",
        )

    searched_train = run_search_mock.call_args.kwargs["market_data"]
    tested_market = run_experiment_mock.call_args.kwargs["market_data"]

    assert searched_train["datetime"].max() < dev_cutoff
    assert tested_market["datetime"].max() < dev_cutoff
    assert result.metadata["holdout_cutoff_date"] == dev_cutoff.isoformat()
    assert result.metadata["development_rows"] == len(train_data)
    assert result.metadata["holdout_rows"] == len(test_data)
    assert result.candidate_evidence.metadata["holdout_cutoff_date"] == dev_cutoff.isoformat()
    assert result.candidate_evidence.metadata["development_rows"] == len(train_data)
    assert result.candidate_evidence.metadata["holdout_rows"] == len(test_data)


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
        "candidate_evidence": {
            "strategy_name": "ma_crossover",
            "strategy_parameters": {"short_window": 2, "long_window": 3},
            "verdict": "validated",
            "search_rank": 1,
            "search_result_count": 1,
            "search_ranking_score": "score",
            "search_score": 0.8,
            "train_metrics": {"total_return": 0.0},
            "test_metrics": {"total_return": 0.0},
            "benchmark_relative_summary": {"benchmark_total_return": 0.0},
            "degradation_summary": {"return_degradation": 0.0, "sharpe_degradation": 0.0, "max_drawdown_delta": 0.0},
            "artifact_paths": {"validation_summary_path": str(tmp_path / "validation_case" / "validation_summary.json")},
            "metadata": {},
        },
        "candidate_decision": {
            "policy_name": "post_search_candidate_policy",
            "policy_scope": "validate-search",
            "verdict": "validated",
            "decision_reasons": ["evidence_complete", "out_of_sample_return_positive"],
        },
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
            artifact_receipt=ValidationArtifactReceipt(
                validation_summary_path=tmp_path / "validation_case" / "validation_summary.json",
                train_ranked_results_path=tmp_path / "validation_case" / "train_ranked_results.csv",
                policy_decision_path=tmp_path / "validation_case" / "policy_decision.json",
            ),
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
    assert Path(payload["policy_decision_path"]).name == "policy_decision.json"
    assert payload["candidate_decision"]["verdict"] == payload["candidate_evidence"]["verdict"]


def test_cli_validate_search_without_permutation_flag_preserves_existing_behavior(
    sample_market_csv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
            "--short-windows",
            "2",
            "--long-windows",
            "3",
            "--split-ratio",
            "0.5",
        ],
    )

    with patch("alphaforge.cli.run_validate_search_with_details") as run_validate_mock, patch(
        "alphaforge.cli.serialize_validation_result", return_value={"ok": True}
    ), patch("alphaforge.cli.serialize_validation_artifact_receipt", return_value=None):
        run_validate_mock.return_value = ValidationExecutionOutput(validation_result=object(), artifact_receipt=None)  # type: ignore[arg-type]
        main()

    assert run_validate_mock.call_args.kwargs["permutation_config"] is None


def test_cli_validate_search_with_permutation_flag_passes_config_into_workflow(
    sample_market_csv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
            "--short-windows",
            "2",
            "--long-windows",
            "3",
            "--split-ratio",
            "0.5",
            "--permutation-test",
            "--permutations",
            "7",
            "--permutation-seed",
            "99",
            "--permutation-block-size",
            "3",
            "--permutation-null-model",
            "return_block_reconstruction",
            "--permutation-scope",
            "test",
        ],
    )

    with patch("alphaforge.cli.run_validate_search_with_details") as run_validate_mock, patch(
        "alphaforge.cli.serialize_validation_result", return_value={"ok": True}
    ), patch("alphaforge.cli.serialize_validation_artifact_receipt", return_value=None):
        run_validate_mock.return_value = ValidationExecutionOutput(validation_result=object(), artifact_receipt=None)  # type: ignore[arg-type]
        main()

    permutation_config = run_validate_mock.call_args.kwargs["permutation_config"]
    assert isinstance(permutation_config, ValidationPermutationConfig)
    assert permutation_config.enabled is True
    assert permutation_config.permutations == 7
    assert permutation_config.seed == 99
    assert permutation_config.block_size == 3
    assert permutation_config.null_model == "return_block_reconstruction"
    assert permutation_config.scope == "test"


def test_run_walk_forward_search_creates_chronological_fold_outputs(sample_market_csv: Path, tmp_path: Path) -> None:
    execution = run_walk_forward_search_with_details(
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
    result = execution.walk_forward_result

    summary_path = tmp_path / "walk_forward_case" / "walk_forward_summary.json"
    fold_results_path = tmp_path / "walk_forward_case" / "fold_results.csv"
    fold_root = tmp_path / "walk_forward_case" / "folds" / "fold_001"

    assert execution.artifact_receipt is not None
    assert execution.artifact_receipt.walk_forward_summary_path == summary_path
    assert execution.artifact_receipt.fold_results_path == fold_results_path
    serialized_receipt = serialize_walk_forward_artifact_receipt(execution.artifact_receipt)
    assert serialized_receipt["walk_forward_summary_path"] == str(summary_path)
    assert serialized_receipt["fold_results_path"] == str(fold_results_path)
    assert not hasattr(result, "walk_forward_summary_path")
    assert not hasattr(result, "fold_results_path")
    assert summary_path.exists()
    assert fold_results_path.exists()
    assert len(result.folds) == 2
    assert result.folds[0].train_end < result.folds[0].test_start
    assert "total_return" in result.folds[0].test_benchmark_summary
    assert "mean_benchmark_total_return" in result.aggregate_benchmark_metrics
    assert result.folds[0].candidate_decision is not None
    assert result.folds[0].candidate_evidence.verdict == result.folds[0].candidate_decision.verdict
    assert result.folds[0].candidate_decision.verdict == result.folds[0].candidate_evidence.verdict
    assert result.walk_forward_decision is not None
    assert result.walk_forward_evidence.verdict == result.walk_forward_decision.verdict
    assert result.walk_forward_decision.verdict == result.walk_forward_evidence.verdict
    assert result.walk_forward_evidence.fold_count == 2
    assert result.walk_forward_evidence.aggregate_test_metrics["fold_count"] == 2
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
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 1, bar_count=1),
        score=0.9,
    )
    train_best_fold_2 = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 3, "long_window": 4}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.08, 0.08, 0.8, -0.09, 0.5, 0.8, 1, bar_count=1),
        score=0.7,
    )
    test_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=train_best_fold_1.strategy_spec,
        backtest_config=train_best_fold_1.backtest_config,
        metrics=MetricReport(0.03, 0.03, 0.5, -0.05, 0.5, 0.6, 1, bar_count=1),
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

    with patch("alphaforge.runner_workflows.load_market_data", return_value=market_data), patch(
        "alphaforge.runner_workflows.run_search_on_market_data",
        side_effect=[
            SearchExecutionOutput(ranked_results=[train_best_fold_1], summary=_make_search_summary([train_best_fold_1])),
            SearchExecutionOutput(ranked_results=[train_best_fold_2], summary=_make_search_summary([train_best_fold_2])),
            SearchExecutionOutput(ranked_results=[train_best_fold_2], summary=_make_search_summary([train_best_fold_2])),
        ],
    ) as run_search_mock, patch(
        "alphaforge.runner_workflows.run_experiment_on_market_data",
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
        "walk_forward_evidence": {
            "verdict": "validated",
            "fold_count": 2,
            "validated_fold_count": 2,
            "skipped_fold_count": 0,
            "aggregate_test_metrics": {"fold_count": 2},
            "aggregate_benchmark_metrics": {"fold_count": 2, "mean_benchmark_total_return": 0.03},
            "artifact_paths": {"walk_forward_summary_path": str(tmp_path / "walk_forward_case" / "walk_forward_summary.json"), "fold_results_path": str(tmp_path / "walk_forward_case" / "fold_results.csv")},
            "metadata": {},
        },
            "walk_forward_decision": {
            "policy_name": "post_search_candidate_policy",
            "policy_scope": "walk-forward",
            "verdict": "validated",
            "decision_reasons": [
                "fold_coverage_complete",
                "aggregate_return_positive",
                "aggregate_pooled_sharpe_positive",
                "aggregate_return_excess_non_negative",
                "aggregate_drawdown_non_worsening",
            ],
        },
    }

    with patch(
        "alphaforge.cli.run_walk_forward_search_with_details",
        return_value=WalkForwardExecutionOutput(
            walk_forward_result=run_walk_forward_search(
                data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
                parameter_grid={"short_window": [2], "long_window": [3]},
                train_size=4,
                test_size=2,
                step_size=2,
                output_dir=tmp_path,
                experiment_name="walk_forward_case",
            ),
            artifact_receipt=WalkForwardArtifactReceipt(
                walk_forward_summary_path=tmp_path / "walk_forward_case" / "walk_forward_summary.json",
                fold_results_path=tmp_path / "walk_forward_case" / "fold_results.csv",
            ),
        ),
    ) as run_walk_forward_mock, patch(
        "alphaforge.cli.serialize_walk_forward_result", return_value=walk_forward_payload
    ):
        main()

    payload = json.loads(capsys.readouterr().out)
    assert run_walk_forward_mock.call_args.kwargs["train_size"] == 4
    assert payload["walk_forward_config"]["step_size"] == 2
    assert payload["aggregate_benchmark_metrics"]["mean_benchmark_total_return"] == 0.03
    assert Path(payload["walk_forward_summary_path"]).name == "walk_forward_summary.json"
    assert Path(payload["fold_results_path"]).name == "fold_results.csv"
    assert payload["walk_forward_decision"]["verdict"] == payload["walk_forward_evidence"]["verdict"]
