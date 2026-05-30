#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from alphaforge.json_utils import write_json_artifact


COMPARISON_CSV = "model_comparison.csv"
COMPARISON_SUMMARY_JSON = "model_comparison_summary.json"
REQUIRED_ARTIFACTS = (
    "ml_demo_summary.json",
    "model/metrics.json",
    "ml_prediction_diagnostics/ml_prediction_summary.json",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a comparison report from existing AlphaForge ML demo run artifacts."
    )
    parser.add_argument(
        "--run",
        action="append",
        required=True,
        help="Run spec in the form model_name=/path/to/run_dir. May be repeated.",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--sort-by",
        default="overall_mae",
        choices=(
            "overall_mae",
            "overall_mse",
            "prediction_rank_ic_mean",
            "prediction_ic_mean",
            "long_short_spread_mean",
            "holdout_total_return",
            "holdout_sharpe_ratio",
        ),
    )
    return parser


def parse_run_specs(specs: list[str]) -> list[tuple[str, Path]]:
    parsed: list[tuple[str, Path]] = []
    seen = set()
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"Invalid --run spec {spec!r}; expected model_name=/path/to/run_dir")
        model_name, run_dir_raw = spec.split("=", 1)
        model_name = model_name.strip()
        if not model_name:
            raise ValueError("model_name in --run spec cannot be empty")
        if model_name in seen:
            raise ValueError(f"Duplicate model_name in --run specs: {model_name}")
        seen.add(model_name)
        parsed.append((model_name, Path(run_dir_raw)))
    return parsed


def load_run_record(model_name: str, run_dir: Path) -> dict[str, Any]:
    missing = [str(run_dir / relative) for relative in REQUIRED_ARTIFACTS if not (run_dir / relative).exists()]
    if missing:
        raise ValueError(f"Run {model_name!r} is missing required artifacts: {missing}")

    demo_summary = _read_json(run_dir / "ml_demo_summary.json")
    model_metrics = _read_json(run_dir / "model" / "metrics.json")
    prediction_summary = _read_json(run_dir / "ml_prediction_diagnostics" / "ml_prediction_summary.json")
    research_summary = _load_optional_research_summary(run_dir, demo_summary)

    record = {
        "model_name": model_name,
        "run_dir": str(run_dir),
        "status": demo_summary.get("status"),
        "feature_cols": _join_list(demo_summary.get("feature_cols")),
        "return_labels_rows": demo_summary.get("return_labels_rows"),
        "supervised_panel_rows": demo_summary.get("supervised_panel_rows"),
        "predictions_rows": demo_summary.get("predictions_rows"),
        "ml_signal_rows": demo_summary.get("ml_signal_rows"),
        "train_row_count": model_metrics.get("train_row_count"),
        "test_row_count": model_metrics.get("test_row_count"),
        "model_mse": model_metrics.get("mse"),
        "model_mae": model_metrics.get("mae"),
        "prediction_label_correlation": model_metrics.get("prediction_label_correlation"),
        "overall_mse": prediction_summary.get("overall_mse"),
        "overall_mae": prediction_summary.get("overall_mae"),
        "prediction_ic_mean": prediction_summary.get("prediction_ic_mean"),
        "prediction_ic_t_stat": prediction_summary.get("prediction_ic_t_stat"),
        "prediction_rank_ic_mean": prediction_summary.get("prediction_rank_ic_mean"),
        "prediction_rank_ic_t_stat": prediction_summary.get("prediction_rank_ic_t_stat"),
        "long_short_spread_mean": prediction_summary.get("long_short_spread_mean"),
        "long_short_observation_count": prediction_summary.get("long_short_observation_count"),
        "has_research_validation": research_summary is not None,
        "validation_mode": None,
        "validation_symbol": None,
        "validation_signal_name": None,
        "nonzero_target_weight_count": None,
        "all_flat_selected_symbol": None,
        "holdout_total_return": None,
        "holdout_annualized_return": None,
        "holdout_sharpe_ratio": None,
        "holdout_max_drawdown": None,
        "holdout_turnover": None,
        "holdout_trade_count": None,
    }
    if research_summary is not None:
        holdout_metrics = _extract_holdout_metrics(research_summary)
        record.update({
            "validation_mode": research_summary.get("validation_mode"),
            "validation_symbol": research_summary.get("symbol"),
            "validation_signal_name": research_summary.get("signal_name"),
            "nonzero_target_weight_count": research_summary.get("nonzero_target_weight_count"),
            "all_flat_selected_symbol": research_summary.get("all_flat_selected_symbol"),
            "holdout_total_return": holdout_metrics.get("total_return"),
            "holdout_annualized_return": holdout_metrics.get("annualized_return"),
            "holdout_sharpe_ratio": holdout_metrics.get("sharpe_ratio"),
            "holdout_max_drawdown": holdout_metrics.get("max_drawdown"),
            "holdout_turnover": holdout_metrics.get("turnover"),
            "holdout_trade_count": holdout_metrics.get("trade_count"),
        })
    return record


def build_comparison(records: list[dict[str, Any]], *, sort_by: str) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    if frame.empty:
        raise ValueError("No run records to compare")
    ascending = sort_by in {"overall_mae", "overall_mse"}
    frame["comparison_rank"] = _rank_series(frame[sort_by], ascending=ascending)
    return frame.sort_values(["comparison_rank", "model_name"], kind="mergesort").reset_index(drop=True)


def build_summary(comparison: pd.DataFrame, *, sort_by: str, output_dir: Path) -> dict[str, Any]:
    best = comparison.iloc[0].to_dict()
    return {
        "status": "ok",
        "stage": "ml_model_comparison_report",
        "model_count": int(len(comparison)),
        "sort_by": sort_by,
        "ranking_contract": _ranking_contract(sort_by),
        "best_model": best.get("model_name"),
        "best_model_rank": int(best.get("comparison_rank")),
        "has_any_research_validation": bool(comparison["has_research_validation"].any()),
        "models": comparison["model_name"].tolist(),
        "paths": {
            "comparison_csv": str(output_dir / COMPARISON_CSV),
            "comparison_summary": str(output_dir / COMPARISON_SUMMARY_JSON),
        },
        "boundary": (
            "Aggregates existing ML demo artifacts. It does not train models, generate predictions, "
            "run backtests, or execute live trades."
        ),
    }


def _load_optional_research_summary(run_dir: Path, demo_summary: dict[str, Any]) -> dict[str, Any] | None:
    explicit = demo_summary.get("paths", {}).get("research_validation_summary")
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(run_dir / "research_validation" / "ml_demo_research_validation_summary.json")
    for candidate in candidates:
        if candidate.exists():
            return _read_json(candidate)
    return None


def _extract_holdout_metrics(research_summary: dict[str, Any]) -> dict[str, Any]:
    nested = research_summary.get("research_validation_summary") or {}
    metrics = nested.get("final_holdout_metrics") or {}
    return metrics if isinstance(metrics, dict) else {}


def _rank_series(values: pd.Series, *, ascending: bool) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.rank(method="min", ascending=ascending, na_option="bottom").astype(int)


def _ranking_contract(sort_by: str) -> str:
    if sort_by in {"overall_mae", "overall_mse"}:
        return f"ascending_{sort_by}_lower_is_better"
    return f"descending_{sort_by}_higher_is_better"


def _join_list(value: Any) -> str | None:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if value is None:
        return None
    return str(value)


def _read_json(path: Path) -> dict[str, Any]:
    with open(path) as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def main() -> None:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_specs = parse_run_specs(args.run)
    records = [load_run_record(model_name, run_dir) for model_name, run_dir in run_specs]
    comparison = build_comparison(records, sort_by=args.sort_by)
    comparison_path = output_dir / COMPARISON_CSV
    comparison.to_csv(comparison_path, index=False)
    summary = build_summary(comparison, sort_by=args.sort_by, output_dir=output_dir)
    write_json_artifact(output_dir / COMPARISON_SUMMARY_JSON, summary)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
