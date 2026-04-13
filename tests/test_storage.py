from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from alphaforge.schemas import (
    BacktestConfig,
    DataSpec,
    ExperimentResult,
    MetricReport,
    StrategySpec,
    ValidationResult,
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
    RANKED_RESULTS_FILENAME,
    TRAIN_RANKED_RESULTS_FILENAME,
    TRADE_LOG_FILENAME,
    VALIDATION_SUMMARY_FILENAME,
    WALK_FORWARD_FOLD_PATH_COLUMN,
    WALK_FORWARD_SUMMARY_FILENAME,
    save_ranked_results_artifact,
    save_ranked_results_with_columns,
    save_single_experiment,
    save_validation_result,
    save_walk_forward_result,
    serialize_artifact_receipt,
    serialize_validation_artifact_receipt,
    serialize_validation_result,
    serialize_walk_forward_artifact_receipt,
    serialize_walk_forward_result,
)


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


def test_save_single_experiment_writes_canonical_persisted_files_and_receipt_refs(tmp_path: Path) -> None:
    result = _make_result(short_window=2, long_window=4)
    equity_curve = _make_equity_curve()
    trades = _make_trade_log()

    persisted_result, receipt = save_single_experiment(tmp_path, "single_case", result, equity_curve, trades)

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
    train_ranked_results_path = save_ranked_results_artifact(
        output_dir=validation_root,
        results=[train_best_result],
        parameter_columns=["short_window", "long_window"],
        filename=TRAIN_RANKED_RESULTS_FILENAME,
    )
    validation_result = ValidationResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        split_config=ValidationSplitConfig(split_ratio=0.5),
        selected_strategy_spec=train_best_result.strategy_spec,
        train_best_result=train_best_result,
        test_result=test_result,
        test_benchmark_summary={"total_return": 0.1, "max_drawdown": -0.05},
        metadata={"train_rows": 4, "test_rows": 4},
    )

    persisted_validation, receipt = save_validation_result(
        validation_root,
        validation_result,
        train_ranked_results_path=train_ranked_results_path,
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
    assert "train_ranked_results_path" not in serialized_validation
    assert serialized_receipt["train_ranked_results_path"] == str(train_ranked_results_path)
    assert serialized_receipt["validation_summary_path"] == str(summary_path)


def test_save_walk_forward_result_writes_summary_and_fold_results_contract(tmp_path: Path) -> None:
    walk_forward_root = tmp_path / "walk_forward_case"
    train_best_result = _make_result(short_window=2, long_window=4, score=0.9)
    test_result = _make_result(short_window=2, long_window=4, score=0.4)
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
    )
    walk_forward_result = WalkForwardResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        walk_forward_config=WalkForwardConfig(train_size=4, test_size=2, step_size=2),
        folds=[fold_result],
        aggregate_test_metrics={"fold_count": 1},
        aggregate_benchmark_metrics={"fold_count": 1, "mean_benchmark_total_return": 0.1},
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
    assert fold_results_frame.loc[0, WALK_FORWARD_FOLD_PATH_COLUMN] == str(walk_forward_root / "folds" / "fold_001")
    assert "walk_forward_summary_path" not in serialized_walk_forward
    assert serialized_receipt["walk_forward_summary_path"] == str(summary_path)
    assert serialized_receipt["fold_results_path"] == str(fold_results_path)


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
