from __future__ import annotations

"""Persistence boundary for AlphaForge experiment artifacts.

This module owns canonical persisted experiment outputs, file naming, directory
layout, and receipt materialization. Report HTML artifacts remain presentation
artifacts and are not part of the canonical persisted experiment contract.
"""

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd

from .backtest import BACKTEST_TRADE_LOG_COLUMNS
from .schemas import (
    CandidateEvidenceSummary,
    CandidatePolicyDecision,
    EquityCurveFrame,
    BacktestConfig,
    DataSpec,
    ExperimentResult,
    MetricReport,
    PermutationTestArtifactReceipt,
    PermutationTestSummary,
    StrategySpec,
    ValidationResult,
    WalkForwardEvidenceSummary,
    WalkForwardFoldResult,
    WalkForwardResult,
)

REPORT_FILENAME = "report.html"
BEST_REPORT_FILENAME = "best_report.html"
SEARCH_REPORT_FILENAME = "search_report.html"

CANONICAL_SINGLE_RUN_FILENAMES = (
    "experiment_config.json",
    "metrics_summary.json",
    "trade_log.csv",
    "equity_curve.csv",
)

CANONICAL_VALIDATION_FILENAMES = (
    "validation_summary.json",
    "train_ranked_results.csv",
    "policy_decision.json",
)

CANONICAL_WALK_FORWARD_FILENAMES = (
    "walk_forward_summary.json",
    "fold_results.csv",
)

RANKED_RESULTS_BASE_COLUMNS = [
    "strategy",
    "total_return",
    "annualized_return",
    "sharpe_ratio",
    "max_drawdown",
    "win_rate",
    "turnover",
    "trade_count",
    "score",
]

TRAIN_RANKED_RESULTS_FILENAME = "train_ranked_results.csv"

EXPERIMENT_CONFIG_FILENAME = "experiment_config.json"
METRICS_SUMMARY_FILENAME = "metrics_summary.json"
TRADE_LOG_FILENAME = "trade_log.csv"
EQUITY_CURVE_FILENAME = "equity_curve.csv"
RANKED_RESULTS_FILENAME = "ranked_results.csv"
VALIDATION_SUMMARY_FILENAME = "validation_summary.json"
POLICY_DECISION_FILENAME = "policy_decision.json"
WALK_FORWARD_SUMMARY_FILENAME = "walk_forward_summary.json"
FOLD_RESULTS_FILENAME = "fold_results.csv"
WALK_FORWARD_FOLD_PATH_COLUMN = "fold_path"
PERMUTATION_TEST_SUMMARY_FILENAME = "permutation_test_summary.json"
PERMUTATION_SCORES_FILENAME = "permutation_scores.csv"

CANONICAL_SEARCH_FILENAMES = (RANKED_RESULTS_FILENAME,)
CANONICAL_SEARCH_REPORT_FILENAMES = (BEST_REPORT_FILENAME, SEARCH_REPORT_FILENAME)


@dataclass(frozen=True)
class ArtifactReceipt:
    """Storage-owned receipt for persisted experiment artifacts.

    Required fields point at canonical persisted experiment outputs:
    run_dir, equity_curve_path, trade_log_path, and metrics_summary_path.
    Optional report fields point at presentation artifacts only.
    """

    run_dir: Path
    equity_curve_path: Path
    trade_log_path: Path
    metrics_summary_path: Path
    best_report_path: Path | None = None
    comparison_report_path: Path | None = None


@dataclass(frozen=True)
class ValidationArtifactReceipt:
    """Storage-owned receipt for persisted validation artifacts."""

    validation_summary_path: Path
    train_ranked_results_path: Path | None = None
    policy_decision_path: Path | None = None


@dataclass(frozen=True)
class WalkForwardArtifactReceipt:
    """Storage-owned receipt for persisted walk-forward artifacts."""

    walk_forward_summary_path: Path
    fold_results_path: Path


@dataclass(frozen=True)
class SearchArtifactReceipt:
    """Storage-owned receipt for persisted search artifacts."""

    search_root: Path | None
    ranked_results_path: Path | None = None
    best_report_path: Path | None = None
    comparison_report_path: Path | None = None


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def serialize_data_spec(data_spec: DataSpec) -> dict[str, Any]:
    payload = asdict(data_spec)
    payload["path"] = str(data_spec.path)
    return payload


def serialize_strategy_spec(strategy_spec: StrategySpec) -> dict[str, Any]:
    return asdict(strategy_spec)


def serialize_backtest_config(backtest_config: BacktestConfig) -> dict[str, Any]:
    return asdict(backtest_config)


def serialize_metric_report(metric_report: MetricReport) -> dict[str, Any]:
    return asdict(metric_report)


def serialize_experiment_result(result: ExperimentResult) -> dict[str, Any]:
    return {
        "data_spec": serialize_data_spec(result.data_spec),
        "strategy_spec": serialize_strategy_spec(result.strategy_spec),
        "backtest_config": serialize_backtest_config(result.backtest_config),
        "metrics": serialize_metric_report(result.metrics),
        "score": result.score,
        "metadata": result.metadata,
    }


def serialize_candidate_evidence_summary(summary: CandidateEvidenceSummary | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    return {
        "strategy_name": summary.strategy_name,
        "strategy_parameters": summary.strategy_parameters,
        "verdict": summary.verdict,
        "search_rank": summary.search_rank,
        "search_result_count": summary.search_result_count,
        "search_ranking_score": summary.search_ranking_score,
        "search_score": summary.search_score,
        "train_metrics": serialize_metric_report(summary.train_metrics) if summary.train_metrics is not None else None,
        "test_metrics": serialize_metric_report(summary.test_metrics) if summary.test_metrics is not None else None,
        "benchmark_relative_summary": summary.benchmark_relative_summary,
        "degradation_summary": summary.degradation_summary,
        "artifact_paths": summary.artifact_paths,
        "metadata": summary.metadata,
    }


def serialize_candidate_policy_decision(decision: CandidatePolicyDecision | None) -> dict[str, Any] | None:
    if decision is None:
        return None
    return {
        "policy_name": decision.policy_name,
        "policy_scope": decision.policy_scope,
        "verdict": decision.verdict,
        "decision_reasons": list(decision.decision_reasons),
    }


def serialize_research_policy_config(config: dict[str, Any] | None) -> dict[str, Any] | None:
    if config is None:
        return None
    return dict(config)


def serialize_research_policy_decision(decision: Any | None) -> dict[str, Any] | None:
    if decision is None:
        return None
    return {
        "candidate_id": getattr(decision, "candidate_id", None),
        "verdict": getattr(decision, "verdict", None),
        "reasons": list(getattr(decision, "reasons", [])),
        "checks": dict(getattr(decision, "checks", {})),
        "max_reruns": int(getattr(decision, "max_reruns", 0)),
        "rerun_count": int(getattr(decision, "rerun_count", 0)),
    }


def serialize_artifact_receipt(receipt: ArtifactReceipt | None) -> dict[str, Any] | None:
    """Serialize storage-owned artifact references and optional report refs."""
    if receipt is None:
        return None
    return {
        "run_dir": str(receipt.run_dir),
        "equity_curve_path": str(receipt.equity_curve_path),
        "trade_log_path": str(receipt.trade_log_path),
        "metrics_summary_path": str(receipt.metrics_summary_path),
        "best_report_path": _serialize_path(receipt.best_report_path),
        "comparison_report_path": _serialize_path(receipt.comparison_report_path),
    }


def serialize_validation_result(result: ValidationResult) -> dict[str, Any]:
    return {
        "data_spec": serialize_data_spec(result.data_spec),
        "split_config": asdict(result.split_config),
        "selected_strategy_spec": serialize_strategy_spec(result.selected_strategy_spec),
        "train_best_result": serialize_experiment_result(result.train_best_result),
        "test_result": serialize_experiment_result(result.test_result),
        "test_benchmark_summary": result.test_benchmark_summary,
        "candidate_evidence": serialize_candidate_evidence_summary(result.candidate_evidence),
        "candidate_decision": serialize_candidate_policy_decision(result.candidate_decision),
        "research_policy_decision": serialize_research_policy_decision(result.research_policy_decision),
        "research_policy_config": serialize_research_policy_config(result.research_policy_config),
        "metadata": result.metadata,
    }


def serialize_validation_artifact_receipt(receipt: ValidationArtifactReceipt | None) -> dict[str, Any] | None:
    if receipt is None:
        return None
    return {
        "validation_summary_path": str(receipt.validation_summary_path),
        "train_ranked_results_path": _serialize_path(receipt.train_ranked_results_path),
        "policy_decision_path": _serialize_path(receipt.policy_decision_path),
    }


def serialize_walk_forward_fold_result(fold: WalkForwardFoldResult) -> dict[str, Any]:
    return {
        "fold_index": fold.fold_index,
        "train_start": fold.train_start,
        "train_end": fold.train_end,
        "test_start": fold.test_start,
        "test_end": fold.test_end,
        "selected_strategy_spec": serialize_strategy_spec(fold.selected_strategy_spec),
        "train_best_result": serialize_experiment_result(fold.train_best_result),
        "test_result": serialize_experiment_result(fold.test_result),
        "test_benchmark_summary": fold.test_benchmark_summary,
        "candidate_evidence": serialize_candidate_evidence_summary(fold.candidate_evidence),
        "candidate_decision": serialize_candidate_policy_decision(fold.candidate_decision),
    }


def serialize_walk_forward_evidence_summary(summary: WalkForwardEvidenceSummary | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    return {
        "verdict": summary.verdict,
        "fold_count": summary.fold_count,
        "validated_fold_count": summary.validated_fold_count,
        "skipped_fold_count": summary.skipped_fold_count,
        "aggregate_test_metrics": summary.aggregate_test_metrics,
        "aggregate_benchmark_metrics": summary.aggregate_benchmark_metrics,
        "artifact_paths": summary.artifact_paths,
        "metadata": summary.metadata,
    }


def serialize_walk_forward_result(result: WalkForwardResult) -> dict[str, Any]:
    return {
        "data_spec": serialize_data_spec(result.data_spec),
        "walk_forward_config": asdict(result.walk_forward_config),
        "folds": [serialize_walk_forward_fold_result(fold) for fold in result.folds],
        "aggregate_test_metrics": result.aggregate_test_metrics,
        "aggregate_benchmark_metrics": result.aggregate_benchmark_metrics,
        "walk_forward_evidence": serialize_walk_forward_evidence_summary(result.walk_forward_evidence),
        "walk_forward_decision": serialize_candidate_policy_decision(result.walk_forward_decision),
        "metadata": result.metadata,
    }


def serialize_walk_forward_artifact_receipt(receipt: WalkForwardArtifactReceipt | None) -> dict[str, Any] | None:
    if receipt is None:
        return None
    return {
        "walk_forward_summary_path": str(receipt.walk_forward_summary_path),
        "fold_results_path": str(receipt.fold_results_path),
    }


def serialize_permutation_test_summary(
    summary: PermutationTestSummary | None,
) -> dict[str, Any] | None:
    if summary is None:
        return None
    return {
        "strategy_name": summary.strategy_name,
        "strategy_parameters": summary.strategy_parameters,
        "target_metric_name": summary.target_metric_name,
        "null_model": summary.null_model,
        "permutation_mode": summary.permutation_mode,
        "block_size": int(summary.block_size),
        "real_observed_metric_value": float(summary.real_observed_metric_value),
        "permutation_metric_values": [float(value) for value in summary.permutation_metric_values],
        "permutation_count": int(summary.permutation_count),
        "seed": int(summary.seed),
        "null_ge_count": int(summary.null_ge_count),
        "empirical_p_value": summary.empirical_p_value,
        "artifact_paths": summary.artifact_paths,
        "metadata": summary.metadata,
    }


def serialize_permutation_test_artifact_receipt(
    receipt: PermutationTestArtifactReceipt | None,
) -> dict[str, Any] | None:
    if receipt is None:
        return None
    return {
        "permutation_test_summary_path": str(receipt.permutation_test_summary_path),
        "permutation_scores_path": str(receipt.permutation_scores_path),
    }


def serialize_search_artifact_receipt(receipt: SearchArtifactReceipt | None) -> dict[str, Any] | None:
    if receipt is None:
        return None
    return {
        "search_root": _serialize_path(receipt.search_root),
        "ranked_results_path": _serialize_path(receipt.ranked_results_path),
        "best_report_path": _serialize_path(receipt.best_report_path),
        "comparison_report_path": _serialize_path(receipt.comparison_report_path),
    }


def serialize_experiment_config(result: ExperimentResult) -> dict[str, Any]:
    return {
        "data_spec": serialize_data_spec(result.data_spec),
        "strategy_spec": serialize_strategy_spec(result.strategy_spec),
        "backtest_config": serialize_backtest_config(result.backtest_config),
        "metadata": result.metadata,
    }


def save_single_experiment(
    output_dir: Path,
    experiment_name: str,
    result: ExperimentResult,
    equity_curve: EquityCurveFrame,
    trades: pd.DataFrame,
) -> tuple[ExperimentResult, ArtifactReceipt]:
    """Write the canonical persisted files for one experiment run.

    The canonical single-run persisted set is:
    experiment_config.json, metrics_summary.json, trade_log.csv, and
    equity_curve.csv.
    """
    target_dir = ensure_output_dir(output_dir / experiment_name)
    config_path = target_dir / EXPERIMENT_CONFIG_FILENAME
    metrics_path = target_dir / METRICS_SUMMARY_FILENAME
    trade_log_path = target_dir / TRADE_LOG_FILENAME
    equity_curve_path = target_dir / EQUITY_CURVE_FILENAME

    _write_json(config_path, serialize_experiment_config(result))
    _write_json(metrics_path, serialize_metric_report(result.metrics))
    trades.reindex(columns=BACKTEST_TRADE_LOG_COLUMNS).to_csv(trade_log_path, index=False)
    equity_curve.to_csv(equity_curve_path, index=False)

    persisted_result = ExperimentResult(
        data_spec=result.data_spec,
        strategy_spec=result.strategy_spec,
        backtest_config=result.backtest_config,
        metrics=result.metrics,
        score=result.score,
        metadata=result.metadata,
    )
    receipt = ArtifactReceipt(
        run_dir=target_dir,
        equity_curve_path=equity_curve_path,
        trade_log_path=trade_log_path,
        metrics_summary_path=metrics_path,
    )
    return persisted_result, receipt


def save_ranked_results(output_dir: Path, results: list[ExperimentResult]) -> Path:
    return save_ranked_results_with_columns(output_dir=output_dir, results=results, parameter_columns=None)


def save_ranked_results_with_columns(
    output_dir: Path,
    results: list[ExperimentResult],
    parameter_columns: list[str] | None,
) -> Path:
    """Write the canonical ranked-results CSV for a search run."""
    ensure_output_dir(output_dir)
    return _save_ranked_results_frame(
        ranked_path=output_dir / RANKED_RESULTS_FILENAME,
        results=results,
        parameter_columns=parameter_columns,
    )


def save_ranked_results_artifact(
    output_dir: Path,
    results: list[ExperimentResult],
    parameter_columns: list[str] | None,
    filename: str,
) -> Path:
    ensure_output_dir(output_dir)
    return _save_ranked_results_frame(
        ranked_path=output_dir / filename,
        results=results,
        parameter_columns=parameter_columns,
    )


def _save_ranked_results_frame(
    ranked_path: Path,
    results: list[ExperimentResult],
    parameter_columns: list[str] | None,
) -> Path:
    rows = []
    discovered_parameter_columns: list[str] = list(parameter_columns or [])
    for result in results:
        for parameter_name in result.strategy_spec.parameters:
            if parameter_name not in discovered_parameter_columns:
                discovered_parameter_columns.append(parameter_name)
        row = {
            "strategy": result.strategy_spec.name,
            **result.strategy_spec.parameters,
            **result.metrics.__dict__,
            "score": result.score,
        }
        rows.append(row)
    ranked_columns = ["strategy", *discovered_parameter_columns, *RANKED_RESULTS_BASE_COLUMNS[1:]]
    pd.DataFrame(rows, columns=ranked_columns).to_csv(ranked_path, index=False)
    return ranked_path


def save_validation_result(
    output_dir: Path,
    validation_result: ValidationResult,
    train_ranked_results_path: Path | None = None,
) -> tuple[ValidationResult, ValidationArtifactReceipt]:
    """Write the canonical persisted validation summary artifact.

    The canonical validation persisted set is validation_summary.json plus the
    train-ranked-results CSV when validation search output is persisted.
    """
    ensure_output_dir(output_dir)
    summary_path = output_dir / VALIDATION_SUMMARY_FILENAME
    policy_decision_path = output_dir / POLICY_DECISION_FILENAME
    receipt = ValidationArtifactReceipt(
        validation_summary_path=summary_path,
        train_ranked_results_path=train_ranked_results_path,
        policy_decision_path=policy_decision_path,
    )
    receipt_payload = serialize_validation_artifact_receipt(receipt) or {}
    _write_json(
        policy_decision_path,
        {
            "research_policy_decision": serialize_research_policy_decision(validation_result.research_policy_decision),
            "research_policy_config": serialize_research_policy_config(validation_result.research_policy_config),
        },
    )
    _write_json(
        summary_path,
        {
            **serialize_validation_result(validation_result),
            **receipt_payload,
        },
    )
    return validation_result, receipt


def save_walk_forward_result(
    output_dir: Path,
    walk_forward_result: WalkForwardResult,
) -> tuple[WalkForwardResult, WalkForwardArtifactReceipt]:
    """Write the canonical persisted walk-forward summary and fold results.

    The canonical walk-forward persisted set is walk_forward_summary.json plus
    fold_results.csv.
    """
    ensure_output_dir(output_dir)
    summary_path = output_dir / WALK_FORWARD_SUMMARY_FILENAME
    fold_results_path = output_dir / FOLD_RESULTS_FILENAME
    receipt = WalkForwardArtifactReceipt(
        walk_forward_summary_path=summary_path,
        fold_results_path=fold_results_path,
    )
    receipt_payload = serialize_walk_forward_artifact_receipt(receipt) or {}
    _write_json(
        summary_path,
        {
            **serialize_walk_forward_result(walk_forward_result),
            **receipt_payload,
        },
    )
    _write_walk_forward_fold_results_csv(fold_results_path, walk_forward_result)
    return walk_forward_result, receipt


def save_permutation_test_result(
    output_dir: Path,
    summary: PermutationTestSummary,
) -> tuple[PermutationTestSummary, PermutationTestArtifactReceipt]:
    """Write the canonical persisted permutation-test summary and score list."""
    ensure_output_dir(output_dir)
    summary_path = output_dir / PERMUTATION_TEST_SUMMARY_FILENAME
    scores_path = output_dir / PERMUTATION_SCORES_FILENAME
    receipt = PermutationTestArtifactReceipt(
        permutation_test_summary_path=summary_path,
        permutation_scores_path=scores_path,
    )
    persisted_summary = replace(
        summary,
        block_size=int(summary.block_size),
        real_observed_metric_value=float(summary.real_observed_metric_value),
        permutation_metric_values=[float(value) for value in summary.permutation_metric_values],
        permutation_count=int(summary.permutation_count),
        seed=int(summary.seed),
        null_ge_count=int(summary.null_ge_count),
        artifact_paths={
            **summary.artifact_paths,
            **serialize_permutation_test_artifact_receipt(receipt),
        },
    )
    _write_json(
        summary_path,
        {
            **serialize_permutation_test_summary(persisted_summary),
            **serialize_permutation_test_artifact_receipt(receipt),
        },
    )
    _write_permutation_scores_csv(scores_path, persisted_summary)
    return persisted_summary, receipt


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _write_walk_forward_fold_results_csv(path: Path, walk_forward_result: WalkForwardResult) -> None:
    parameter_columns: list[str] = []
    for fold in walk_forward_result.folds:
        for parameter_name in fold.selected_strategy_spec.parameters:
            if parameter_name not in parameter_columns:
                parameter_columns.append(parameter_name)

    fixed_columns = [
        "fold_index",
        "train_start",
        "train_end",
        "test_start",
        "test_end",
    ]
    metric_columns = [
        "train_score",
        "train_total_return",
        "train_sharpe_ratio",
        "test_total_return",
        "test_annualized_return",
        "test_sharpe_ratio",
        "test_max_drawdown",
        "test_win_rate",
        "test_turnover",
        "test_trade_count",
        "benchmark_total_return",
        "benchmark_max_drawdown",
        WALK_FORWARD_FOLD_PATH_COLUMN,
    ]
    rows = []
    for fold in walk_forward_result.folds:
        row = {
            "fold_index": fold.fold_index,
            "train_start": fold.train_start,
            "train_end": fold.train_end,
            "test_start": fold.test_start,
            "test_end": fold.test_end,
            "train_score": fold.train_best_result.score,
            "train_total_return": fold.train_best_result.metrics.total_return,
            "train_sharpe_ratio": fold.train_best_result.metrics.sharpe_ratio,
            "test_total_return": fold.test_result.metrics.total_return,
            "test_annualized_return": fold.test_result.metrics.annualized_return,
            "test_sharpe_ratio": fold.test_result.metrics.sharpe_ratio,
            "test_max_drawdown": fold.test_result.metrics.max_drawdown,
            "test_win_rate": fold.test_result.metrics.win_rate,
            "test_turnover": fold.test_result.metrics.turnover,
            "test_trade_count": fold.test_result.metrics.trade_count,
            "benchmark_total_return": fold.test_benchmark_summary.get("total_return"),
            "benchmark_max_drawdown": fold.test_benchmark_summary.get("max_drawdown"),
            WALK_FORWARD_FOLD_PATH_COLUMN: str(_materialize_walk_forward_fold_dir(path.parent, fold.fold_index)),
        }
        for parameter_name in parameter_columns:
            row[parameter_name] = fold.selected_strategy_spec.parameters.get(parameter_name)
        rows.append(row)
    pd.DataFrame(rows, columns=fixed_columns + parameter_columns + metric_columns).to_csv(path, index=False)


def _write_permutation_scores_csv(path: Path, summary: PermutationTestSummary) -> None:
    rows = [
        {
            "permutation_index": index,
            "metric_value": metric_value,
        }
        for index, metric_value in enumerate(summary.permutation_metric_values, start=1)
    ]
    pd.DataFrame(rows, columns=["permutation_index", "metric_value"]).to_csv(path, index=False)


def _materialize_walk_forward_fold_dir(output_dir: Path, fold_index: int) -> Path:
    return output_dir / "folds" / f"fold_{fold_index:03d}"


def _serialize_path(path: Path | None) -> str | None:
    return str(path) if path else None
