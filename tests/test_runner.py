from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from alphaforge.experiment_runner import (
    ExperimentExecutionOutput,
    SearchExecutionOutput,
    run_strategy_comparison_with_details,
    run_experiment,
    run_experiment_with_artifacts,
    run_research_validation_protocol_with_details,
    run_search,
    run_search_with_details,
    run_validate_search,
    run_walk_forward_search,
)
from alphaforge.report import ExperimentReportInput
from alphaforge.search_reporting import save_best_search_report
from alphaforge.schemas import (
    BacktestConfig,
    DataSpec,
    ExperimentResult,
    MetricReport,
    ResearchPeriod,
    ResearchValidationConfig,
    SearchSummary,
    StrategyComparisonConfig,
    StrategyFamilySearchConfig,
    StrategySpec,
    ValidationPermutationConfig,
    ValidationSplitConfig,
    WalkForwardConfig,
    WalkForwardResult,
)
from alphaforge.storage import ArtifactReceipt, serialize_experiment_result
from alphaforge.backtest import build_execution_semantics_metadata


def _make_research_protocol_market_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=12, freq="D"),
            "open": [100.0 + index for index in range(12)],
            "high": [101.0 + index for index in range(12)],
            "low": [99.0 + index for index in range(12)],
            "close": [100.0 + index for index in range(12)],
            "volume": [1000.0] * 12,
        }
    )


def _make_protocol_result(sample_market_csv: Path, parameters: dict[str, int], score: float) -> ExperimentResult:
    return ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters=parameters),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(
            total_return=score / 10.0,
            annualized_return=score / 10.0,
            sharpe_ratio=score,
            max_drawdown=-0.01,
            win_rate=1.0,
            turnover=1.0,
            trade_count=1,
            bar_count=3,
        ),
        score=score,
    )


def _make_protocol_execution(result: ExperimentResult) -> ExperimentExecutionOutput:
    return ExperimentExecutionOutput(
        result=result,
        equity_curve=pd.DataFrame(),
        trade_log=pd.DataFrame(),
        report_input=ExperimentReportInput(
            result=result,
            equity_curve=pd.DataFrame(),
            trades=pd.DataFrame(),
            benchmark_summary={"total_return": 0.0, "max_drawdown": 0.0},
            benchmark_curve=pd.DataFrame(),
        ),
        artifact_receipt=None,
    )


def _make_research_validation_config(sample_market_csv: Path) -> ResearchValidationConfig:
    return ResearchValidationConfig(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_name="ma_crossover",
        parameter_grid={"short_window": [2], "long_window": [4]},
        development_period=ResearchPeriod(start="2024-01-01", end="2024-01-08"),
        holdout_period=ResearchPeriod(start="2024-01-09", end="2024-01-12"),
        walk_forward_config=WalkForwardConfig(train_size=3, test_size=2, step_size=2),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
    )


def test_run_experiment_saves_outputs(sample_market_csv: Path, tmp_path: Path) -> None:
    execution = run_experiment_with_artifacts(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(
            name="ma_crossover",
            parameters={"short_window": 2, "long_window": 3},
        ),
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="runner_case",
    )

    assert execution.artifact_receipt is not None
    assert execution.artifact_receipt.trade_log_path.name == "trade_log.csv"
    assert execution.artifact_receipt.equity_curve_path.name == "equity_curve.csv"
    assert execution.artifact_receipt.metrics_summary_path.name == "metrics_summary.json"
    assert not hasattr(execution.result, "metrics_path")
    assert execution.result.metrics.trade_count >= 0
    assert {key: execution.result.metadata[key] for key in build_execution_semantics_metadata()} == build_execution_semantics_metadata()
    assert not execution.equity_curve.empty
    assert isinstance(execution.trade_log, pd.DataFrame)


def test_run_experiment_saved_artifacts_match_returned_metrics_and_trades(
    sample_market_csv: Path,
    tmp_path: Path,
) -> None:
    result, _, trades = run_experiment(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(
            name="ma_crossover",
            parameters={"short_window": 2, "long_window": 3},
        ),
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="artifact_match_case",
    )

    metrics_payload = json.loads((tmp_path / "artifact_match_case" / "metrics_summary.json").read_text(encoding="utf-8"))
    experiment_config_payload = json.loads((tmp_path / "artifact_match_case" / "experiment_config.json").read_text(encoding="utf-8"))
    trade_log_frame = pd.read_csv(tmp_path / "artifact_match_case" / "trade_log.csv")

    assert metrics_payload["trade_count"] == result.metrics.trade_count
    assert metrics_payload["bar_count"] == result.metrics.bar_count
    assert metrics_payload["turnover"] == result.metrics.turnover
    assert metrics_payload["total_return"] == result.metrics.total_return
    assert experiment_config_payload["metadata"] == result.metadata
    assert len(trade_log_frame) == len(trades)
    assert trade_log_frame.columns.tolist() == trades.columns.tolist()


def test_run_search_ranks_multiple_parameter_sets(sample_market_csv: Path, tmp_path: Path) -> None:
    ranked = run_search(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"short_window": [2, 3], "long_window": [4, 5]},
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="search_case",
    )

    assert len(ranked) == 4
    assert ranked[0].score >= ranked[-1].score
    assert (tmp_path / "search_case" / "ranked_results.csv").exists()


def test_run_search_saves_ranked_results_and_per_run_artifacts_under_search_root(
    sample_market_csv: Path,
    tmp_path: Path,
) -> None:
    ranked = run_search(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"short_window": [2, 3], "long_window": [4]},
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="search_layout_case",
    )

    search_root = tmp_path / "search_layout_case"
    runs_root = search_root / "runs"

    assert len(ranked) == 2
    assert (search_root / "ranked_results.csv").exists()
    assert (runs_root / "run_001" / "experiment_config.json").exists()
    assert (runs_root / "run_001" / "metrics_summary.json").exists()
    assert (runs_root / "run_001" / "trade_log.csv").exists()
    assert (runs_root / "run_001" / "equity_curve.csv").exists()
    assert (runs_root / "run_002" / "experiment_config.json").exists()


def test_run_search_with_details_returns_explicit_artifact_paths(sample_market_csv: Path, tmp_path: Path) -> None:
    search_execution = run_search_with_details(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"short_window": [2, 3], "long_window": [4]},
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="search_details_case",
        generate_best_report=True,
    )

    assert len(search_execution.ranked_results) == 2
    assert search_execution.artifact_receipt is not None
    assert search_execution.artifact_receipt.search_root == tmp_path / "search_details_case"
    assert search_execution.artifact_receipt.ranked_results_path == tmp_path / "search_details_case" / "ranked_results.csv"
    assert search_execution.artifact_receipt.best_report_path == tmp_path / "search_details_case" / "best_report.html"
    assert search_execution.artifact_receipt.comparison_report_path == tmp_path / "search_details_case" / "search_report.html"
    assert search_execution.summary.strategy_name == "ma_crossover"
    assert search_execution.summary.search_parameter_names == ["short_window", "long_window"]
    assert search_execution.summary.attempted_combinations == 2
    assert search_execution.summary.valid_combinations == 2
    assert search_execution.summary.invalid_combinations == 0
    assert search_execution.summary.result_count == 2
    assert search_execution.summary.best_result == search_execution.ranked_results[0]
    assert search_execution.summary.top_results == search_execution.ranked_results[:2]
    assert not hasattr(search_execution, "ranked_results_path")
    assert not hasattr(search_execution, "best_report_path")
    assert not hasattr(search_execution, "comparison_report_path")


def test_run_search_with_details_without_holdout_cutoff_uses_full_dataset(sample_market_csv: Path) -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=6, freq="D"),
            "open": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "high": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "low": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "close": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "volume": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        }
    )
    train_best = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 1, bar_count=1),
        score=0.9,
    )

    with patch("alphaforge.runner_workflows.load_market_data", return_value=market_data), patch(
        "alphaforge.runner_workflows.run_search_on_market_data",
        return_value=SearchExecutionOutput(
            ranked_results=[train_best],
            summary=SearchSummary(
                strategy_name="ma_crossover",
                search_parameter_names=["short_window", "long_window"],
                attempted_combinations=1,
                valid_combinations=1,
                invalid_combinations=0,
                result_count=1,
                ranking_score="score",
                best_result=train_best,
                top_results=[train_best],
            ),
        ),
    ) as run_search_mock:
        run_search_with_details(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid={"short_window": [2], "long_window": [4]},
        )

    assert run_search_mock.call_args.kwargs["market_data"].equals(market_data)


def test_run_search_summary_counts_invalid_combinations_and_top_results_prefix(
    sample_market_csv: Path,
    tmp_path: Path,
) -> None:
    search_execution = run_search_with_details(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"short_window": [2, 4], "long_window": [3, 4, 5]},
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="search_summary_case",
    )

    assert search_execution.summary.attempted_combinations == 6
    assert search_execution.summary.valid_combinations == 4
    assert search_execution.summary.invalid_combinations == 2
    assert search_execution.summary.result_count == len(search_execution.ranked_results)
    assert search_execution.summary.best_result == search_execution.ranked_results[0]
    assert search_execution.summary.top_results == search_execution.ranked_results[:3]


def test_research_validation_workflow_uses_development_data_for_search_and_walk_forward(
    sample_market_csv: Path,
) -> None:
    market_data = _make_research_protocol_market_data()
    selected_result = _make_protocol_result(sample_market_csv, {"short_window": 2, "long_window": 4}, score=0.8)
    final_result = _make_protocol_result(sample_market_csv, {"short_window": 2, "long_window": 4}, score=0.2)

    def fake_search(**kwargs):
        passed_data = kwargs["market_data"]
        assert passed_data["datetime"].max() <= pd.Timestamp("2024-01-08")
        assert passed_data["datetime"].min() >= pd.Timestamp("2024-01-01")
        return SearchExecutionOutput(
            ranked_results=[selected_result],
            summary=SearchSummary(
                strategy_name="ma_crossover",
                search_parameter_names=["short_window", "long_window"],
                attempted_combinations=1,
                valid_combinations=1,
                invalid_combinations=0,
                result_count=1,
                ranking_score="score",
                best_result=selected_result,
                top_results=[selected_result],
            ),
        )

    def fake_walk_forward(**kwargs):
        passed_data = kwargs["market_data"]
        assert passed_data["datetime"].max() <= pd.Timestamp("2024-01-08")
        return (
            WalkForwardResult(
                data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
                walk_forward_config=WalkForwardConfig(train_size=3, test_size=2, step_size=2),
                folds=[],
                aggregate_test_metrics={"fold_count": 0},
                metadata={"evidence_label": "development_period_oos"},
            ),
            None,
        )

    with patch("alphaforge.runner_workflows.load_market_data", return_value=market_data), patch(
        "alphaforge.runner_workflows.run_search_on_market_data",
        side_effect=fake_search,
    ), patch(
        "alphaforge.runner_workflows.run_walk_forward_search_on_market_data",
        side_effect=fake_walk_forward,
    ), patch(
        "alphaforge.runner_workflows.run_experiment_on_market_data",
        return_value=_make_protocol_execution(final_result),
    ) as final_holdout_mock:
        execution = run_research_validation_protocol_with_details(
            _make_research_validation_config(sample_market_csv)
        )

    final_market_data = final_holdout_mock.call_args.kwargs["market_data"]
    assert final_market_data["datetime"].min() >= pd.Timestamp("2024-01-09")
    assert execution.research_protocol_summary.development_search_data_window == {
        "label": "development_period",
        "start": "2024-01-01 00:00:00",
        "end": "2024-01-08 00:00:00",
        "row_count": 8,
    }
    assert execution.research_protocol_summary.walk_forward_data_window["label"] == "development_period_oos"
    assert execution.research_protocol_summary.final_holdout_data_window == {
        "label": "final_holdout",
        "start": "2024-01-09 00:00:00",
        "end": "2024-01-12 00:00:00",
        "row_count": 4,
    }
    assert execution.research_protocol_summary.selected_parameters == {"short_window": 2, "long_window": 4}
    assert execution.research_protocol_summary.walk_forward_summary.metadata["evidence_label"] == "development_period_oos"


def test_research_validation_workflow_evaluates_holdout_with_frozen_selected_candidate(
    sample_market_csv: Path,
) -> None:
    market_data = _make_research_protocol_market_data()
    selected_result = _make_protocol_result(sample_market_csv, {"short_window": 2, "long_window": 4}, score=0.8)
    lower_result = _make_protocol_result(sample_market_csv, {"short_window": 3, "long_window": 5}, score=0.7)
    final_result = _make_protocol_result(sample_market_csv, {"short_window": 2, "long_window": 4}, score=99.0)
    search_summary = SearchSummary(
        strategy_name="ma_crossover",
        search_parameter_names=["short_window", "long_window"],
        attempted_combinations=2,
        valid_combinations=2,
        invalid_combinations=0,
        result_count=2,
        ranking_score="score",
        best_result=selected_result,
        top_results=[selected_result, lower_result],
    )

    with patch("alphaforge.runner_workflows.load_market_data", return_value=market_data), patch(
        "alphaforge.runner_workflows.run_search_on_market_data",
        return_value=SearchExecutionOutput(ranked_results=[selected_result, lower_result], summary=search_summary),
    ), patch(
        "alphaforge.runner_workflows.run_walk_forward_search_on_market_data",
        return_value=(
            WalkForwardResult(
                data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
                walk_forward_config=WalkForwardConfig(train_size=3, test_size=2, step_size=2),
                folds=[],
                aggregate_test_metrics={},
            ),
            None,
        ),
    ), patch(
        "alphaforge.runner_workflows.run_experiment_on_market_data",
        return_value=_make_protocol_execution(final_result),
    ) as final_holdout_mock:
        execution = run_research_validation_protocol_with_details(
            _make_research_validation_config(sample_market_csv)
        )

    assert final_holdout_mock.call_args.kwargs["strategy_spec"].parameters == {"short_window": 2, "long_window": 4}
    assert execution.research_protocol_summary.frozen_plan.selected_parameters == {"short_window": 2, "long_window": 4}
    assert execution.research_protocol_summary.final_holdout_result.score == 99.0
    assert execution.research_protocol_summary.selected_parameters == {"short_window": 2, "long_window": 4}


def test_run_search_with_details_supports_breakout_family(sample_market_csv: Path, tmp_path: Path) -> None:
    search_execution = run_search_with_details(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"lookback_window": [2, 4]},
        strategy_name="breakout",
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="breakout_search_case",
    )

    assert search_execution.summary.strategy_name == "breakout"
    assert search_execution.summary.search_parameter_names == ["lookback_window"]
    assert all(result.strategy_spec.name == "breakout" for result in search_execution.ranked_results)


def test_run_validate_search_supports_breakout_family(sample_market_csv: Path, tmp_path: Path) -> None:
    validation_result = run_validate_search(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"lookback_window": [2, 4]},
        split_ratio=0.5,
        strategy_name="breakout",
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="breakout_validation_case",
    )

    assert validation_result.selected_strategy_spec.name == "breakout"
    assert "lookback_window" in validation_result.selected_strategy_spec.parameters
    assert validation_result.candidate_evidence.strategy_name == "breakout"


def test_run_strategy_comparison_compares_ma_and_breakout(sample_market_csv: Path, tmp_path: Path) -> None:
    execution = run_strategy_comparison_with_details(
        StrategyComparisonConfig(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            split_config=ValidationSplitConfig(split_ratio=0.5),
            backtest_config=BacktestConfig(
                initial_capital=1000,
                fee_rate=0.0,
                slippage_rate=0.0,
                annualization_factor=252,
            ),
            strategy_families=[
                StrategyFamilySearchConfig(
                    strategy_name="ma_crossover",
                    parameter_grid={"short_window": [2], "long_window": [3, 4]},
                ),
                StrategyFamilySearchConfig(
                    strategy_name="breakout",
                    parameter_grid={"lookback_window": [2, 3]},
                ),
            ],
            output_dir=tmp_path,
            experiment_name="comparison_case",
        )
    )

    summary = execution.comparison_summary
    result_by_strategy = {result.strategy_name: result for result in summary.comparison_results}

    assert set(result_by_strategy) == {"ma_crossover", "breakout"}
    assert result_by_strategy["ma_crossover"].selected_strategy_spec.name == "ma_crossover"
    assert result_by_strategy["breakout"].selected_strategy_spec.name == "breakout"
    assert all(result.research_policy_verdict is not None for result in summary.comparison_results)
    assert all(result.candidate_policy_verdict is not None for result in summary.comparison_results)
    assert all(result.permutation_status == "skipped" for result in summary.comparison_results)
    assert execution.artifact_receipt is not None
    assert execution.artifact_receipt.comparison_summary_path.exists()
    assert execution.artifact_receipt.comparison_results_path.exists()
    assert (tmp_path / "comparison_case" / "strategies" / "ma_crossover" / "validation_summary.json").exists()
    assert (tmp_path / "comparison_case" / "strategies" / "breakout" / "validation_summary.json").exists()
    assert summary.metadata["ranking_contract"] == "research_policy_verdict_group_then_descending_test_score"


def test_run_strategy_comparison_propagates_permutation_summary_per_family(
    sample_market_csv: Path,
    tmp_path: Path,
) -> None:
    execution = run_strategy_comparison_with_details(
        StrategyComparisonConfig(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            split_config=ValidationSplitConfig(split_ratio=0.5),
            backtest_config=BacktestConfig(
                initial_capital=1000,
                fee_rate=0.0,
                slippage_rate=0.0,
                annualization_factor=252,
            ),
            strategy_families=[
                StrategyFamilySearchConfig(
                    strategy_name="ma_crossover",
                    parameter_grid={"short_window": [2], "long_window": [3]},
                ),
                StrategyFamilySearchConfig(
                    strategy_name="breakout",
                    parameter_grid={"lookback_window": [2]},
                ),
            ],
            permutation_config=ValidationPermutationConfig(
                enabled=True,
                permutations=2,
                seed=7,
                block_size=2,
                null_model="return_block_reconstruction",
                scope="test",
            ),
            output_dir=tmp_path,
            experiment_name="comparison_permutation_case",
        )
    )

    result_by_strategy = {result.strategy_name: result for result in execution.comparison_summary.comparison_results}

    assert result_by_strategy["ma_crossover"].validation_result.candidate_evidence.permutation_summary.strategy_name == "ma_crossover"
    assert result_by_strategy["breakout"].validation_result.candidate_evidence.permutation_summary.strategy_name == "breakout"
    assert result_by_strategy["ma_crossover"].permutation_status in {"completed_passed", "completed_failed"}
    assert result_by_strategy["breakout"].permutation_status in {"completed_passed", "completed_failed"}
    assert (
        tmp_path
        / "comparison_permutation_case"
        / "strategies"
        / "ma_crossover"
        / "permutation_test"
        / "permutation_test_summary.json"
    ).exists()
    assert (
        tmp_path
        / "comparison_permutation_case"
        / "strategies"
        / "breakout"
        / "permutation_test"
        / "permutation_test_summary.json"
    ).exists()


def test_run_strategy_comparison_rejects_unsupported_strategy(sample_market_csv: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported strategy"):
        run_strategy_comparison_with_details(
            StrategyComparisonConfig(
                data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
                split_config=ValidationSplitConfig(split_ratio=0.5),
                backtest_config=BacktestConfig(
                    initial_capital=1000,
                    fee_rate=0.0,
                    slippage_rate=0.0,
                    annualization_factor=252,
                ),
                strategy_families=[
                    StrategyFamilySearchConfig(
                        strategy_name="not_supported",
                        parameter_grid={"window": [2]},
                    ),
                ],
            )
        )


def test_run_walk_forward_search_supports_breakout_family(sample_market_csv: Path, tmp_path: Path) -> None:
    walk_forward_result = run_walk_forward_search(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"lookback_window": [2, 4]},
        train_size=4,
        test_size=2,
        step_size=2,
        strategy_name="breakout",
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="breakout_walk_forward_case",
    )

    assert walk_forward_result.folds
    assert all(fold.selected_strategy_spec.name == "breakout" for fold in walk_forward_result.folds)
    assert walk_forward_result.walk_forward_evidence is not None
    assert walk_forward_result.walk_forward_decision is not None


def test_run_search_saves_empty_ranked_results_with_headers(sample_market_csv: Path, tmp_path: Path) -> None:
    ranked = run_search(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"short_window": [2], "long_window": [4]},
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="filtered_search_case",
        min_trade_count=10,
    )

    ranked_path = tmp_path / "filtered_search_case" / "ranked_results.csv"
    ranked_frame = pd.read_csv(ranked_path)

    assert ranked == []
    assert ranked_path.exists()
    assert ranked_frame.empty
    assert ranked_frame.columns.tolist() == [
        "strategy",
        "short_window",
        "long_window",
        "total_return",
        "annualized_return",
        "sharpe_ratio",
        "max_drawdown",
        "win_rate",
        "turnover",
        "trade_count",
        "score",
    ]


def test_run_search_generates_exactly_one_best_report(sample_market_csv: Path, tmp_path: Path) -> None:
    with patch("alphaforge.runner_workflows.save_best_search_report", side_effect=lambda search_root, best_result, artifact_receipt: search_root / "best_report.html") as save_best_report, patch(
        "alphaforge.runner_workflows.save_search_comparison_report",
        side_effect=lambda search_root, ranked_results, artifact_receipts, best_report_path, top_n=5: search_root / "search_report.html",
    ) as save_search_report:
        ranked = run_search(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid={"short_window": [2, 3], "long_window": [4, 5]},
            backtest_config=BacktestConfig(
                initial_capital=1000,
                fee_rate=0.0,
                slippage_rate=0.0,
                annualization_factor=252,
            ),
            output_dir=tmp_path,
            experiment_name="search_report_case",
            generate_best_report=True,
        )

    assert len(ranked) == 4
    assert save_best_report.call_count == 1
    assert save_search_report.call_count == 1
    assert save_best_report.call_args.kwargs["search_root"] == tmp_path / "search_report_case"
    assert save_search_report.call_args.kwargs["search_root"] == tmp_path / "search_report_case"


def test_run_search_generates_empty_search_report_without_best_report(sample_market_csv: Path, tmp_path: Path) -> None:
    with patch("alphaforge.runner_workflows.save_best_search_report") as save_best_report, patch(
        "alphaforge.runner_workflows.save_search_comparison_report",
        side_effect=lambda search_root, ranked_results, artifact_receipts, best_report_path, top_n=5: search_root / "search_report.html",
    ) as save_search_report:
        ranked = run_search(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid={"short_window": [2], "long_window": [4]},
            backtest_config=BacktestConfig(
                initial_capital=1000,
                fee_rate=0.0,
                slippage_rate=0.0,
                annualization_factor=252,
            ),
            output_dir=tmp_path,
            experiment_name="empty_search_report_case",
            min_trade_count=10,
            generate_best_report=True,
        )

    assert ranked == []
    assert save_best_report.call_count == 0
    assert save_search_report.call_count == 1
    assert save_search_report.call_args.kwargs["search_root"] == tmp_path / "empty_search_report_case"


def test_run_experiment_with_artifacts_delegates_to_runner_workflows(sample_market_csv: Path) -> None:
    sample_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 3}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 1, bar_count=1),
        score=0.5,
    )
    bundled = ExperimentExecutionOutput(
        result=sample_result,
        equity_curve=pd.DataFrame(),
        trade_log=pd.DataFrame(),
        report_input=object(),
        artifact_receipt=ArtifactReceipt(
            run_dir=Path("run_dir"),
            equity_curve_path=Path("run_dir/equity_curve.csv"),
            trade_log_path=Path("run_dir/trade_log.csv"),
            metrics_summary_path=Path("run_dir/metrics_summary.json"),
        ),
    )

    with patch(
        "alphaforge.runner_workflows.run_experiment_with_artifacts_workflow",
        return_value=bundled,
    ) as workflow_mock:
        delegated = run_experiment_with_artifacts(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 3}),
            backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        )

    assert delegated == bundled
    assert workflow_mock.call_count == 1
    assert workflow_mock.call_args.kwargs["strategy_spec"].parameters == {"short_window": 2, "long_window": 3}


def test_run_search_with_details_delegates_to_runner_workflows(sample_market_csv: Path) -> None:
    sample_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 1, bar_count=1),
        score=0.5,
    )
    expected = SearchExecutionOutput(
        ranked_results=[sample_result],
        summary=SearchSummary(
            strategy_name="ma_crossover",
            search_parameter_names=["short_window", "long_window"],
            attempted_combinations=1,
            valid_combinations=1,
            invalid_combinations=0,
            result_count=1,
            ranking_score="score",
            best_result=sample_result,
            top_results=[sample_result],
        ),
        artifact_receipt=None,
    )

    with patch(
        "alphaforge.runner_workflows.run_search_with_details_workflow",
        return_value=expected,
    ) as workflow_mock:
        delegated = run_search_with_details(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            parameter_grid={"short_window": [2], "long_window": [4]},
            backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        )

    assert delegated == expected
    assert workflow_mock.call_count == 1
    assert workflow_mock.call_args.kwargs["parameter_grid"] == {"short_window": [2], "long_window": [4]}


def test_best_search_report_reads_artifacts_from_receipt_not_runtime_result(tmp_path: Path) -> None:
    search_root = tmp_path / "search_case"
    run_dir = search_root / "runs" / "run_001"
    run_dir.mkdir(parents=True)
    equity_curve_path = run_dir / "equity_curve.csv"
    trade_log_path = run_dir / "trade_log.csv"
    pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=3, freq="D"),
            "close": [100.0, 101.0, 103.0],
            "equity": [1000.0, 1010.0, 1030.0],
        }
    ).to_csv(equity_curve_path, index=False)
    pd.DataFrame(
        {
            "entry_datetime": ["2024-01-02 00:00:00"],
            "exit_datetime": ["2024-01-03 00:00:00"],
            "entry_price": [101.0],
            "exit_price": [103.0],
            "holding_period": [1],
            "trade_gross_return": [0.019801980198019802],
            "trade_net_return": [0.018801980198019803],
            "cost_return_contribution": [0.001],
            "entry_target_position": [1.0],
            "exit_target_position": [0.0],
        }
    ).to_csv(trade_log_path, index=False)
    best_result = ExperimentResult(
        data_spec=DataSpec(path=Path("sample_data/a.csv"), symbol="2330"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(100000.0, 0.001, 0.0005, 252),
        metrics=MetricReport(0.2, 0.3, 1.4, -0.08, 0.6, 1.2, 4, bar_count=1),
        score=0.9,
    )
    receipt = ArtifactReceipt(
        run_dir=run_dir,
        equity_curve_path=equity_curve_path,
        trade_log_path=trade_log_path,
        metrics_summary_path=run_dir / "metrics_summary.json",
    )

    with patch("alphaforge.search_reporting.save_experiment_report", side_effect=lambda content, path: path) as save_report:
        report_path = save_best_search_report(search_root=search_root, best_result=best_result, artifact_receipt=receipt)

    assert report_path == search_root / "best_report.html"
    assert save_report.call_count == 1


def test_storage_serializes_runtime_result_without_runtime_owned_to_dict(sample_market_csv: Path) -> None:
    result, _, _ = run_experiment(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(
            name="ma_crossover",
            parameters={"short_window": 2, "long_window": 3},
        ),
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
    )

    payload = serialize_experiment_result(result)

    assert payload["data_spec"]["symbol"] == "TEST"
    assert payload["strategy_spec"]["parameters"] == {"short_window": 2, "long_window": 3}
    assert "equity_curve_path" not in payload
    assert "trade_log_path" not in payload
    assert "metrics_path" not in payload
    assert not hasattr(result, "to_dict")


def test_runtime_result_remains_valid_domain_truth_without_artifact_paths(sample_market_csv: Path) -> None:
    result, _, _ = run_experiment(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(
            name="ma_crossover",
            parameters={"short_window": 2, "long_window": 3},
        ),
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
    )

    assert result.metrics.trade_count >= 0
    assert result.strategy_spec.parameters == {"short_window": 2, "long_window": 3}
    assert not hasattr(result, "equity_curve_path")
    assert not hasattr(result, "trade_log_path")
