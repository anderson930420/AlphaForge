from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .schemas import EquityCurveFrame, RANKED_RESULTS_BASE_COLUMNS, TRADE_LOG_COLUMNS, ExperimentResult, ValidationResult


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_single_experiment(
    output_dir: Path,
    experiment_name: str,
    result: ExperimentResult,
    equity_curve: EquityCurveFrame,
    trades: pd.DataFrame,
) -> ExperimentResult:
    target_dir = ensure_output_dir(output_dir / experiment_name)
    config_path = target_dir / "experiment_config.json"
    metrics_path = target_dir / "metrics_summary.json"
    trade_log_path = target_dir / "trade_log.csv"
    equity_curve_path = target_dir / "equity_curve.csv"

    _write_json(config_path, _serialize_config(result))
    _write_json(metrics_path, result.metrics.__dict__)
    trades.reindex(columns=TRADE_LOG_COLUMNS).to_csv(trade_log_path, index=False)
    equity_curve.to_csv(equity_curve_path, index=False)

    return ExperimentResult(
        data_spec=result.data_spec,
        strategy_spec=result.strategy_spec,
        backtest_config=result.backtest_config,
        metrics=result.metrics,
        score=result.score,
        equity_curve_path=equity_curve_path,
        trade_log_path=trade_log_path,
        metrics_path=metrics_path,
        metadata=result.metadata,
    )


def save_ranked_results(output_dir: Path, results: list[ExperimentResult]) -> Path:
    return save_ranked_results_with_columns(output_dir=output_dir, results=results, parameter_columns=None)


def save_ranked_results_with_columns(
    output_dir: Path,
    results: list[ExperimentResult],
    parameter_columns: list[str] | None,
) -> Path:
    ensure_output_dir(output_dir)
    ranked_path = output_dir / "ranked_results.csv"
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


def save_validation_result(output_dir: Path, validation_result: ValidationResult) -> ValidationResult:
    ensure_output_dir(output_dir)
    summary_path = output_dir / "validation_summary.json"
    persisted_result = ValidationResult(
        data_spec=validation_result.data_spec,
        split_config=validation_result.split_config,
        selected_strategy_spec=validation_result.selected_strategy_spec,
        train_best_result=validation_result.train_best_result,
        test_result=validation_result.test_result,
        validation_summary_path=summary_path,
        train_ranked_results_path=validation_result.train_ranked_results_path,
        metadata=validation_result.metadata,
    )
    _write_json(summary_path, persisted_result.to_dict())
    return persisted_result


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _serialize_config(result: ExperimentResult) -> dict[str, Any]:
    return {
        "data_spec": {
            "path": str(result.data_spec.path),
            "symbol": result.data_spec.symbol,
            "datetime_column": result.data_spec.datetime_column,
        },
        "strategy_spec": {
            "name": result.strategy_spec.name,
            "parameters": result.strategy_spec.parameters,
        },
        "backtest_config": result.backtest_config.__dict__,
        "metadata": result.metadata,
    }
