from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from alphaforge.evidence import build_candidate_evidence_summary, build_walk_forward_evidence_summary
from alphaforge.research_policy import PolicyDecision
from alphaforge.schemas import (
    BacktestConfig,
    DataSpec,
    ExperimentResult,
    MetricReport,
    CandidatePolicyDecision,
    PermutationTestArtifactReceipt,
    PermutationTestSummary,
    SearchSummary,
    StrategySpec,
    ValidationResult,
    ValidationPermutationConfig,
    ValidationSplitConfig,
    WalkForwardConfig,
    WalkForwardFoldResult,
    WalkForwardResult,
)
from alphaforge.storage import (
    ArtifactReceipt,
    CANONICAL_SEARCH_FILENAMES,
    CANONICAL_SINGLE_RUN_FILENAMES,
    CANONICAL_VALIDATION_FILENAMES,
    CANONICAL_WALK_FORWARD_FILENAMES,
    EQUITY_CURVE_FILENAME,
    FOLD_RESULTS_FILENAME,
    METRICS_SUMMARY_FILENAME,
    PERMUTATION_SCORES_FILENAME,
    PERMUTATION_TEST_SUMMARY_FILENAME,
    RANKED_RESULTS_FILENAME,
    POLICY_DECISION_FILENAME,
    TRAIN_RANKED_RESULTS_FILENAME,
    TRADE_LOG_FILENAME,
    VALIDATION_SUMMARY_FILENAME,
    WALK_FORWARD_FOLD_PATH_COLUMN,
    WALK_FORWARD_SUMMARY_FILENAME,
    save_ranked_results_artifact,
    save_ranked_results_with_columns,
    save_permutation_test_result,
    save_single_experiment,
    save_validation_result,
    save_walk_forward_result,
    serialize_artifact_receipt,
    serialize_search_artifact_receipt,
    serialize_permutation_test_artifact_receipt,
    serialize_validation_artifact_receipt,
    serialize_validation_result,
    serialize_walk_forward_artifact_receipt,
    serialize_walk_forward_result,
    SearchArtifactReceipt,
)
from alphaforge.permutation import NULL_MODEL


def _make_result(short_window: int, long_window: int, score: float = 0.5) -> ExperimentResult:
    return ExperimentResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": short_window, "long_window": long_window}),
        backtest_config=BacktestConfig(initial_capital=100000.0, fee_rate=0.001, slippage_rate=0.0005, annualization_factor=252),
        metrics=MetricReport(
            total_return=0.2,
            annualized_return=0.3,
            sharpe_ratio=1.4,
            max_drawdown=-0.08,
            win_rate=0.6,
            turnover=1.2,
            trade_count=4,
        ),
        score=score,
    )


def _make_breakout_result(lookback_window: int, score: float = 0.5) -> ExperimentResult:
    return ExperimentResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        strategy_spec=StrategySpec(name="breakout", parameters={"lookback_window": lookback_window}),
        backtest_config=BacktestConfig(initial_capital=100000.0, fee_rate=0.001, slippage_rate=0.0005, annualization_factor=252),
        metrics=MetricReport(
            total_return=0.18,
            annualized_return=0.28,
            sharpe_ratio=1.2,
            max_drawdown=-0.07,
            win_rate=0.55,
            turnover=1.1,
            trade_count=3,
        ),
        score=score,
    )


def _make_equity_curve() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=3, freq="D"),
            "position": [0.0, 1.0, 1.0],
            "turnover": [0.0, 1.0, 0.0],
            "strategy_return": [0.0, 0.01, 0.02],
            "equity": [100000.0, 101000.0, 103000.0],
            "close": [100.0, 101.0, 103.0],
        }
    )


def _make_trade_log() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "entry_time": ["2024-01-02 00:00:00"],
            "exit_time": ["2024-01-03 00:00:00"],
            "side": ["long"],
            "quantity": [1.0],
            "entry_price": [101.0],
            "exit_price": [103.0],
            "gross_return": [0.019801980198019802],
            "net_pnl": [2.0],
        }
    )


def _make_search_summary(result: ExperimentResult, result_count: int = 1) -> SearchSummary:
    return SearchSummary(
        strategy_name=result.strategy_spec.name,
        search_parameter_names=list(result.strategy_spec.parameters),
        attempted_combinations=result_count,
        valid_combinations=result_count,
        invalid_combinations=0,
        result_count=result_count,
        ranking_score="score",
        best_result=result,
        top_results=[result],
    )


def test_save_single_experiment_writes_canonical_persisted_files_and_receipt_refs(tmp_path: Path) -> None:
    result = _make_result(short_window=2, long_window=4)
    equity_curve = _make_equity_curve()
    trades = _make_trade_log()

    persisted_result, receipt = save_single_experiment(tmp_path, "single_case", result, equity_curve, trades)
    metrics_payload = json.loads((tmp_path / "single_case" / METRICS_SUMMARY_FILENAME).read_text(encoding="utf-8"))

    run_dir = tmp_path / "single_case"
    assert run_dir.exists()
    for filename in CANONICAL_SINGLE_RUN_FILENAMES:
        assert (run_dir / filename).exists()
    assert receipt.run_dir == run_dir
    assert receipt.equity_curve_path.name == EQUITY_CURVE_FILENAME
    assert receipt.trade_log_path.name == TRADE_LOG_FILENAME
    assert receipt.metrics_summary_path.name == METRICS_SUMMARY_FILENAME
    assert receipt.best_report_path is None
    assert receipt.comparison_report_path is None
    assert metrics_payload["bar_count"] == result.metrics.bar_count
    assert not hasattr(persisted_result, "equity_curve_path")
    assert not hasattr(persisted_result, "trade_log_path")
    assert not hasattr(persisted_result, "metrics_path")

    serialized_receipt = serialize_artifact_receipt(receipt)
    assert serialized_receipt["run_dir"] == str(run_dir)
    assert serialized_receipt["best_report_path"] is None
    assert serialized_receipt["comparison_report_path"] is None


def test_save_ranked_results_writes_canonical_search_contract(tmp_path: Path) -> None:
    search_root = tmp_path / "search_case"
    runs_root = search_root / "runs"
    result_one = _make_result(short_window=2, long_window=4, score=0.9)
    result_two = _make_result(short_window=3, long_window=5, score=0.8)

    ranked_results_path = save_ranked_results_with_columns(
        output_dir=search_root,
        results=[result_one, result_two],
        parameter_columns=["short_window", "long_window"],
    )
    save_single_experiment(runs_root, "run_001", result_one, _make_equity_curve(), _make_trade_log())
    save_single_experiment(runs_root, "run_002", result_two, _make_equity_curve(), _make_trade_log())

    ranked_frame = pd.read_csv(ranked_results_path)
    assert ranked_results_path.name == RANKED_RESULTS_FILENAME
    assert ranked_results_path.parent == search_root
    for filename in CANONICAL_SEARCH_FILENAMES:
        assert (search_root / filename).exists()
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
    assert (runs_root / "run_001" / EQUITY_CURVE_FILENAME).exists()
    assert (runs_root / "run_001" / TRADE_LOG_FILENAME).exists()
    assert (runs_root / "run_002" / METRICS_SUMMARY_FILENAME).exists()


def test_save_validation_result_writes_summary_and_train_ranked_reference(tmp_path: Path) -> None:
    validation_root = tmp_path / "validation_case"
    train_best_result = _make_result(short_window=2, long_window=4, score=0.9)
    test_result = _make_result(short_window=2, long_window=4, score=0.4)
    permutation_summary = PermutationTestSummary(
        strategy_name="ma_crossover",
        strategy_parameters={"short_window": 2, "long_window": 4},
        target_metric_name="score",
        permutation_mode="block",
        block_size=2,
        real_observed_metric_value=0.42,
        permutation_metric_values=[0.1, 0.2, 0.3],
        permutation_count=3,
        seed=11,
        null_ge_count=1,
        empirical_p_value=0.04,
        null_model="return_block_reconstruction",
        metadata={"permutation_scope": "test"},
    )
    search_summary = _make_search_summary(train_best_result)
    train_ranked_results_path = save_ranked_results_artifact(
        output_dir=validation_root,
        results=[train_best_result],
        parameter_columns=["short_window", "long_window"],
        filename=TRAIN_RANKED_RESULTS_FILENAME,
    )
    persisted_permutation_summary, permutation_receipt = save_permutation_test_result(validation_root, permutation_summary)
    validation_result = ValidationResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        split_config=ValidationSplitConfig(split_ratio=0.5),
        selected_strategy_spec=train_best_result.strategy_spec,
        train_best_result=train_best_result,
        test_result=test_result,
        test_benchmark_summary={"total_return": 0.1, "max_drawdown": -0.05},
        permutation_config=ValidationPermutationConfig(enabled=True, permutations=3, seed=11, block_size=2),
        research_policy_decision=PolicyDecision(
            candidate_id="ma_crossover:{'short_window': 2, 'long_window': 4}",
            verdict="promote",
            reasons=["trade_count 4 meets minimum 1", "all configured research policy checks passed"],
            checks={"rerun_count_within_limit": True, "test_metrics_present": True, "min_trade_count": True},
            max_reruns=0,
            rerun_count=0,
        ),
        research_policy_config={
            "max_reruns": 0,
            "min_trade_count": 1,
            "max_drawdown_cap": None,
            "min_return_degradation": 0.0,
            "max_permutation_p_value": None,
            "required_permutation_null_model": None,
            "required_permutation_scope": None,
        },
        candidate_evidence=build_candidate_evidence_summary(
            strategy_spec=train_best_result.strategy_spec,
            train_result=train_best_result,
            test_result=test_result,
            search_summary=search_summary,
            benchmark_summary={"total_return": 0.1, "max_drawdown": -0.05},
            permutation_summary=persisted_permutation_summary,
            permutation_status="run_passed",
            artifact_paths={
                "validation_summary_path": str(validation_root / VALIDATION_SUMMARY_FILENAME),
                "train_ranked_results_path": str(train_ranked_results_path),
                "permutation_test_summary_path": str(permutation_receipt.permutation_test_summary_path),
                "permutation_scores_path": str(permutation_receipt.permutation_scores_path),
            },
        ),
        candidate_decision=CandidatePolicyDecision(
            policy_name="post_search_candidate_policy",
            policy_scope="validate-search",
            verdict="validated",
            decision_reasons=["evidence_complete", "out_of_sample_return_positive"],
        ),
        metadata={"train_rows": 4, "test_rows": 4},
    )

    persisted_validation, receipt = save_validation_result(
        validation_root,
        validation_result,
        train_ranked_results_path=train_ranked_results_path,
        permutation_artifact_receipt=permutation_receipt,
    )
    summary_path = validation_root / VALIDATION_SUMMARY_FILENAME
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    serialized_validation = serialize_validation_result(persisted_validation)
    serialized_receipt = serialize_validation_artifact_receipt(receipt)

    assert summary_path.exists()
    for filename in CANONICAL_VALIDATION_FILENAMES:
        assert (validation_root / filename).exists()
    assert summary_payload["train_ranked_results_path"] == str(train_ranked_results_path)
    assert summary_payload["validation_summary_path"] == str(summary_path)
    assert summary_payload["permutation_test_summary_path"] == str(permutation_receipt.permutation_test_summary_path)
    assert summary_payload["permutation_scores_path"] == str(permutation_receipt.permutation_scores_path)
    assert summary_payload["candidate_evidence"]["verdict"] == "validated"
    assert summary_payload["candidate_evidence"]["permutation_status"] == "run_passed"
    assert summary_payload["candidate_evidence"]["permutation_summary"]["empirical_p_value"] == 0.04
    assert summary_payload["candidate_decision"]["verdict"] == "validated"
    assert summary_payload["research_policy_decision"]["verdict"] == "promote"
    assert summary_payload["policy_decision_path"] == str(validation_root / POLICY_DECISION_FILENAME)
    assert summary_payload["candidate_evidence"]["search_rank"] == 1
    assert summary_payload["candidate_evidence"]["artifact_paths"]["validation_summary_path"] == str(summary_path)
    assert summary_payload["candidate_evidence"]["artifact_paths"]["permutation_test_summary_path"] == str(
        permutation_receipt.permutation_test_summary_path
    )
    assert summary_payload["candidate_evidence"]["artifact_paths"]["permutation_scores_path"] == str(permutation_receipt.permutation_scores_path)
    assert "train_ranked_results_path" not in serialized_validation
    assert serialized_receipt["train_ranked_results_path"] == str(train_ranked_results_path)
    assert serialized_receipt["validation_summary_path"] == str(summary_path)
    assert serialized_receipt["policy_decision_path"] == str(validation_root / POLICY_DECISION_FILENAME)
    assert serialized_receipt["permutation_test_summary_path"] == str(permutation_receipt.permutation_test_summary_path)
    assert serialized_receipt["permutation_scores_path"] == str(permutation_receipt.permutation_scores_path)
    assert (validation_root / "permutation_test_summary.json").exists()
    assert (validation_root / "permutation_scores.csv").exists()


def test_save_validation_result_writes_policy_decision_artifact(tmp_path: Path) -> None:
    validation_root = tmp_path / "validation_policy_case"
    train_best_result = _make_result(short_window=2, long_window=4, score=0.9)
    test_result = _make_result(short_window=2, long_window=4, score=0.4)
    validation_result = ValidationResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        split_config=ValidationSplitConfig(split_ratio=0.5),
        selected_strategy_spec=train_best_result.strategy_spec,
        train_best_result=train_best_result,
        test_result=test_result,
        test_benchmark_summary={"total_return": 0.1, "max_drawdown": -0.05},
        research_policy_decision=PolicyDecision(
            candidate_id="candidate-123",
            verdict="reject",
            reasons=["trade_count 0 below minimum 2"],
            checks={"rerun_count_within_limit": True, "test_metrics_present": True, "min_trade_count": False},
            max_reruns=0,
            rerun_count=0,
        ),
        research_policy_config={
            "max_reruns": 0,
            "min_trade_count": 2,
            "max_drawdown_cap": None,
            "min_return_degradation": 0.0,
            "max_permutation_p_value": None,
            "required_permutation_null_model": None,
            "required_permutation_scope": None,
        },
        candidate_evidence=build_candidate_evidence_summary(
            strategy_spec=train_best_result.strategy_spec,
            train_result=train_best_result,
            test_result=test_result,
            search_summary=_make_search_summary(train_best_result),
            benchmark_summary={"total_return": 0.1, "max_drawdown": -0.05},
            artifact_paths={
                "validation_summary_path": str(validation_root / VALIDATION_SUMMARY_FILENAME),
            },
        ),
    )

    _, receipt = save_validation_result(validation_root, validation_result)
    summary_payload = json.loads((validation_root / VALIDATION_SUMMARY_FILENAME).read_text(encoding="utf-8"))
    policy_payload = json.loads((validation_root / POLICY_DECISION_FILENAME).read_text(encoding="utf-8"))

    assert (validation_root / POLICY_DECISION_FILENAME).exists()
    assert summary_payload["policy_decision_path"] == str(validation_root / POLICY_DECISION_FILENAME)
    assert policy_payload["research_policy_decision"]["candidate_id"] == "candidate-123"
    assert policy_payload["research_policy_decision"]["verdict"] == "reject"
    assert policy_payload["research_policy_config"]["min_trade_count"] == 2
    assert receipt.policy_decision_path == validation_root / POLICY_DECISION_FILENAME


def test_save_walk_forward_result_writes_summary_and_fold_results_contract(tmp_path: Path) -> None:
    walk_forward_root = tmp_path / "walk_forward_case"
    train_best_result = _make_result(short_window=2, long_window=4, score=0.9)
    test_result = _make_result(short_window=2, long_window=4, score=0.4)
    search_summary = _make_search_summary(train_best_result, result_count=2)
    fold_result = WalkForwardFoldResult(
        fold_index=1,
        train_start="2024-01-01",
        train_end="2024-01-04",
        test_start="2024-01-05",
        test_end="2024-01-06",
        selected_strategy_spec=train_best_result.strategy_spec,
        train_best_result=train_best_result,
        test_result=test_result,
        test_benchmark_summary={"total_return": 0.1, "max_drawdown": -0.05},
        candidate_evidence=build_candidate_evidence_summary(
            strategy_spec=train_best_result.strategy_spec,
            train_result=train_best_result,
            test_result=test_result,
            search_summary=search_summary,
            benchmark_summary={"total_return": 0.1, "max_drawdown": -0.05},
            artifact_paths={
                "fold_root": str(walk_forward_root / "folds" / "fold_001"),
                "train_search_root": str(walk_forward_root / "folds" / "fold_001" / "train_search"),
                "test_selected_run_dir": str(walk_forward_root / "folds" / "fold_001" / "test_selected"),
            },
        ),
        candidate_decision=CandidatePolicyDecision(
            policy_name="post_search_candidate_policy",
            policy_scope="walk-forward",
            verdict="validated",
            decision_reasons=["evidence_complete", "out_of_sample_return_positive"],
        ),
    )
    walk_forward_result = WalkForwardResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        walk_forward_config=WalkForwardConfig(train_size=4, test_size=2, step_size=2),
        folds=[fold_result],
        aggregate_test_metrics={"fold_count": 1},
        aggregate_benchmark_metrics={"fold_count": 1, "mean_benchmark_total_return": 0.1},
        walk_forward_evidence=build_walk_forward_evidence_summary(
            fold_count=1,
            validated_fold_count=1,
            skipped_fold_count=0,
            aggregate_test_metrics={"fold_count": 1},
            aggregate_benchmark_metrics={"fold_count": 1, "mean_benchmark_total_return": 0.1},
            artifact_paths={
                "walk_forward_summary_path": str(walk_forward_root / WALK_FORWARD_SUMMARY_FILENAME),
                "fold_results_path": str(walk_forward_root / FOLD_RESULTS_FILENAME),
            },
        ),
        walk_forward_decision=CandidatePolicyDecision(
            policy_name="post_search_candidate_policy",
            policy_scope="walk-forward",
            verdict="validated",
            decision_reasons=[
                "fold_coverage_complete",
                "aggregate_return_positive",
                "aggregate_pooled_sharpe_positive",
                "aggregate_return_excess_non_negative",
                "aggregate_drawdown_non_worsening",
            ],
        ),
        metadata={"fold_count": 1},
    )

    persisted_result, receipt = save_walk_forward_result(walk_forward_root, walk_forward_result)
    summary_path = walk_forward_root / WALK_FORWARD_SUMMARY_FILENAME
    fold_results_path = walk_forward_root / FOLD_RESULTS_FILENAME
    fold_results_frame = pd.read_csv(fold_results_path)
    serialized_walk_forward = serialize_walk_forward_result(persisted_result)
    serialized_receipt = serialize_walk_forward_artifact_receipt(receipt)

    assert summary_path.exists()
    assert fold_results_path.exists()
    for filename in CANONICAL_WALK_FORWARD_FILENAMES:
        assert (walk_forward_root / filename).exists()
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary_payload["walk_forward_summary_path"] == str(summary_path)
    assert summary_payload["fold_results_path"] == str(fold_results_path)
    assert summary_payload["walk_forward_evidence"]["verdict"] == "validated"
    assert summary_payload["walk_forward_decision"]["verdict"] == "validated"
    assert summary_payload["walk_forward_evidence"]["fold_count"] == 1
    assert summary_payload["folds"][0]["candidate_evidence"]["verdict"] == "validated"
    assert summary_payload["folds"][0]["candidate_decision"]["verdict"] == "validated"
    assert fold_results_frame.loc[0, WALK_FORWARD_FOLD_PATH_COLUMN] == str(walk_forward_root / "folds" / "fold_001")
    assert "walk_forward_summary_path" not in serialized_walk_forward
    assert serialized_receipt["walk_forward_summary_path"] == str(summary_path)
    assert serialized_receipt["fold_results_path"] == str(fold_results_path)


def test_save_walk_forward_result_writes_breakout_parameter_columns(tmp_path: Path) -> None:
    walk_forward_root = tmp_path / "walk_forward_breakout_case"
    train_best_result = _make_breakout_result(lookback_window=5, score=0.9)
    test_result = _make_breakout_result(lookback_window=5, score=0.4)
    search_summary = _make_search_summary(train_best_result, result_count=1)
    fold_result = WalkForwardFoldResult(
        fold_index=1,
        train_start="2024-01-01",
        train_end="2024-01-04",
        test_start="2024-01-05",
        test_end="2024-01-06",
        selected_strategy_spec=train_best_result.strategy_spec,
        train_best_result=train_best_result,
        test_result=test_result,
        test_benchmark_summary={"total_return": 0.1, "max_drawdown": -0.05},
        candidate_evidence=build_candidate_evidence_summary(
            strategy_spec=train_best_result.strategy_spec,
            train_result=train_best_result,
            test_result=test_result,
            search_summary=search_summary,
            benchmark_summary={"total_return": 0.1, "max_drawdown": -0.05},
            artifact_paths={
                "fold_root": str(walk_forward_root / "folds" / "fold_001"),
                "train_search_root": str(walk_forward_root / "folds" / "fold_001" / "train_search"),
                "test_selected_run_dir": str(walk_forward_root / "folds" / "fold_001" / "test_selected"),
            },
        ),
        candidate_decision=CandidatePolicyDecision(
            policy_name="post_search_candidate_policy",
            policy_scope="walk-forward",
            verdict="validated",
            decision_reasons=["evidence_complete"],
        ),
    )
    walk_forward_result = WalkForwardResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        walk_forward_config=WalkForwardConfig(train_size=4, test_size=2, step_size=2),
        folds=[fold_result],
        aggregate_test_metrics={"fold_count": 1},
        aggregate_benchmark_metrics={"fold_count": 1, "mean_benchmark_total_return": 0.1},
        walk_forward_evidence=build_walk_forward_evidence_summary(
            fold_count=1,
            validated_fold_count=1,
            skipped_fold_count=0,
            aggregate_test_metrics={"fold_count": 1},
            aggregate_benchmark_metrics={"fold_count": 1, "mean_benchmark_total_return": 0.1},
            artifact_paths={
                "walk_forward_summary_path": str(walk_forward_root / WALK_FORWARD_SUMMARY_FILENAME),
                "fold_results_path": str(walk_forward_root / FOLD_RESULTS_FILENAME),
            },
        ),
        walk_forward_decision=CandidatePolicyDecision(
            policy_name="post_search_candidate_policy",
            policy_scope="walk-forward",
            verdict="validated",
            decision_reasons=["fold_coverage_complete"],
        ),
        metadata={"fold_count": 1},
    )

    persisted_result, receipt = save_walk_forward_result(walk_forward_root, walk_forward_result)
    fold_results_frame = pd.read_csv(walk_forward_root / FOLD_RESULTS_FILENAME)
    serialized_receipt = serialize_walk_forward_artifact_receipt(receipt)

    assert persisted_result.folds[0].selected_strategy_spec.name == "breakout"
    assert fold_results_frame.columns.tolist().count("lookback_window") == 1
    assert "short_window" not in fold_results_frame.columns
    assert "long_window" not in fold_results_frame.columns
    assert serialized_receipt["walk_forward_summary_path"] == str(walk_forward_root / WALK_FORWARD_SUMMARY_FILENAME)


def test_save_permutation_test_result_writes_canonical_summary_and_scores(tmp_path: Path) -> None:
    summary = PermutationTestSummary(
        strategy_name="ma_crossover",
        strategy_parameters={"short_window": 2, "long_window": 4},
        target_metric_name="score",
        permutation_mode="block",
        block_size="2",  # type: ignore[arg-type]
        real_observed_metric_value=0.42,
        permutation_metric_values=[0.1, 0.2, 0.3],
        permutation_count="3",  # type: ignore[arg-type]
        seed="11",  # type: ignore[arg-type]
        null_ge_count="1",  # type: ignore[arg-type]
        empirical_p_value=0.5,
        metadata={"source": "unit-test"},
    )

    persisted_summary, receipt = save_permutation_test_result(tmp_path / "permutation_case", summary)
    summary_path = tmp_path / "permutation_case" / PERMUTATION_TEST_SUMMARY_FILENAME
    scores_path = tmp_path / "permutation_case" / PERMUTATION_SCORES_FILENAME
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    scores_frame = pd.read_csv(scores_path)
    serialized_receipt = serialize_permutation_test_artifact_receipt(receipt)

    assert summary_path.exists()
    assert scores_path.exists()
    assert summary_payload["strategy_name"] == "ma_crossover"
    assert summary_payload["null_model"] == NULL_MODEL
    assert summary_payload["permutation_mode"] == "block"
    assert summary_payload["block_size"] == 2
    assert isinstance(summary_payload["permutation_count"], int)
    assert isinstance(summary_payload["seed"], int)
    assert isinstance(summary_payload["null_ge_count"], int)
    assert summary_payload["real_observed_metric_value"] == 0.42
    assert summary_payload["null_ge_count"] == 1
    assert summary_payload["empirical_p_value"] == 0.5
    assert isinstance(persisted_summary.permutation_count, int)
    assert isinstance(persisted_summary.seed, int)
    assert isinstance(persisted_summary.null_ge_count, int)
    assert summary_payload["artifact_paths"]["permutation_test_summary_path"] == str(summary_path)
    assert summary_payload["artifact_paths"]["permutation_scores_path"] == str(scores_path)
    assert persisted_summary.artifact_paths["permutation_test_summary_path"] == str(summary_path)
    assert persisted_summary.artifact_paths["permutation_scores_path"] == str(scores_path)
    assert serialized_receipt["permutation_test_summary_path"] == str(summary_path)
    assert serialized_receipt["permutation_scores_path"] == str(scores_path)
    assert scores_frame.columns.tolist() == ["permutation_index", "metric_value"]
    assert scores_frame["metric_value"].tolist() == [0.1, 0.2, 0.3]


def test_serialize_artifact_receipt_separates_persisted_and_presentation_refs(tmp_path: Path) -> None:
    receipt = ArtifactReceipt(
        run_dir=tmp_path / "run_001",
        equity_curve_path=tmp_path / "run_001" / EQUITY_CURVE_FILENAME,
        trade_log_path=tmp_path / "run_001" / TRADE_LOG_FILENAME,
        metrics_summary_path=tmp_path / "run_001" / METRICS_SUMMARY_FILENAME,
        best_report_path=tmp_path / "search_case" / "best_report.html",
        comparison_report_path=tmp_path / "search_case" / "search_report.html",
    )

    serialized = serialize_artifact_receipt(receipt)

    assert serialized["run_dir"] == str(tmp_path / "run_001")
    assert serialized["equity_curve_path"] == str(tmp_path / "run_001" / EQUITY_CURVE_FILENAME)
    assert serialized["trade_log_path"] == str(tmp_path / "run_001" / TRADE_LOG_FILENAME)
    assert serialized["metrics_summary_path"] == str(tmp_path / "run_001" / METRICS_SUMMARY_FILENAME)
    assert serialized["best_report_path"] == str(tmp_path / "search_case" / "best_report.html")
    assert serialized["comparison_report_path"] == str(tmp_path / "search_case" / "search_report.html")


def test_serialize_search_artifact_receipt_tracks_ranked_and_report_paths(tmp_path: Path) -> None:
    receipt = SearchArtifactReceipt(
        search_root=tmp_path / "search_case",
        ranked_results_path=tmp_path / "search_case" / "ranked_results.csv",
        best_report_path=tmp_path / "search_case" / "best_report.html",
        comparison_report_path=tmp_path / "search_case" / "search_report.html",
    )

    serialized = serialize_search_artifact_receipt(receipt)

    assert serialized["search_root"] == str(tmp_path / "search_case")
    assert serialized["ranked_results_path"] == str(tmp_path / "search_case" / "ranked_results.csv")
    assert serialized["best_report_path"] == str(tmp_path / "search_case" / "best_report.html")
    assert serialized["comparison_report_path"] == str(tmp_path / "search_case" / "search_report.html")
