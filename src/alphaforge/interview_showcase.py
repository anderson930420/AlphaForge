from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_INTERVIEW_RUN_DIR = "artifacts/demo/interview_ml_demo_C"
RESEARCH_SUMMARY_RELATIVE = "research_validation/ml_demo_research_validation_summary.json"
FINAL_HOLDOUT_RELATIVE = "research_validation/ml_signal_single_symbol_validation/final_holdout"


@dataclass(frozen=True)
class InterviewShowcaseArtifacts:
    run_dir: Path
    ml_demo_summary: dict[str, Any] | None
    research_summary: dict[str, Any] | None
    signal: pd.DataFrame | None
    derived_signal: pd.DataFrame | None
    predictions: pd.DataFrame | None
    equity_curve: pd.DataFrame | None
    trade_log: pd.DataFrame | None
    final_holdout_metrics: dict[str, Any] | None
    html_report_path: Path


def load_interview_showcase_artifacts(run_dir: Path | str) -> InterviewShowcaseArtifacts:
    run_dir = Path(run_dir)
    research_summary = _read_json_optional(run_dir / RESEARCH_SUMMARY_RELATIVE)
    derived_signal_path = _research_path(research_summary, "derived_single_symbol_signal")
    return InterviewShowcaseArtifacts(
        run_dir=run_dir,
        ml_demo_summary=_read_json_optional(run_dir / "ml_demo_summary.json"),
        research_summary=research_summary,
        signal=_read_csv_optional(run_dir / "signal" / "ml_signal.csv"),
        derived_signal=_read_csv_optional(derived_signal_path) if derived_signal_path else None,
        predictions=_read_csv_optional(run_dir / "model" / "predictions.csv"),
        equity_curve=_read_csv_optional(run_dir / FINAL_HOLDOUT_RELATIVE / "equity_curve.csv"),
        trade_log=_read_csv_optional(run_dir / FINAL_HOLDOUT_RELATIVE / "trade_log.csv"),
        final_holdout_metrics=_read_json_optional(
            run_dir / FINAL_HOLDOUT_RELATIVE / "metrics_summary.json"
        ),
        html_report_path=run_dir / "interview_artifact_report.html",
    )


def build_health_checks(research_summary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if research_summary is None:
        return [{"check": "research summary exists", "status": "fail", "value": "missing"}]

    nonzero = int(research_summary.get("nonzero_target_weight_count", 0))
    extra_signal_dates = research_summary.get("date_alignment", {}).get("extra_signal_dates")
    warnings = research_summary.get("warnings", [])
    all_flat = bool(research_summary.get("all_flat_selected_symbol", True))

    return [
        {
            "check": "nonzero exposure",
            "status": "pass" if nonzero > 0 else "fail",
            "value": nonzero,
        },
        {
            "check": "signal dates covered by market data",
            "status": "pass" if extra_signal_dates == [] else "fail",
            "value": extra_signal_dates,
        },
        {
            "check": "selected symbol is not all-flat",
            "status": "pass" if not all_flat else "fail",
            "value": all_flat,
        },
        {
            "check": "warnings",
            "status": "pass" if warnings == [] else "warn",
            "value": warnings,
        },
    ]


def summarize_signal_exposure(signal: pd.DataFrame | None) -> pd.DataFrame:
    if signal is None or signal.empty or "symbol" not in signal.columns or "target_weight" not in signal.columns:
        return pd.DataFrame(columns=["symbol", "rows", "nonzero_target_weight_count", "total_abs_weight"])
    frame = signal.copy()
    frame["target_weight"] = pd.to_numeric(frame["target_weight"], errors="coerce").fillna(0.0)
    frame["nonzero"] = frame["target_weight"].abs() > 0.0
    return (
        frame.groupby("symbol", dropna=False)
        .agg(
            rows=("symbol", "size"),
            nonzero_target_weight_count=("nonzero", "sum"),
            total_abs_weight=("target_weight", lambda s: float(s.abs().sum())),
        )
        .reset_index()
    )


def extract_overview_metrics(artifacts: InterviewShowcaseArtifacts) -> dict[str, Any]:
    demo = artifacts.ml_demo_summary or {}
    research = artifacts.research_summary or {}
    final_metrics = artifacts.final_holdout_metrics or {}
    return {
        "model": demo.get("model"),
        "predictions_rows": demo.get("predictions_rows"),
        "ml_signal_rows": demo.get("ml_signal_rows"),
        "does_run_research_validation": demo.get("does_run_research_validation"),
        "symbol": research.get("symbol"),
        "selected_signal_row_count": research.get("selected_signal_row_count"),
        "nonzero_target_weight_count": research.get("nonzero_target_weight_count"),
        "total_return": final_metrics.get("total_return"),
        "sharpe_ratio": final_metrics.get("sharpe_ratio"),
        "max_drawdown": final_metrics.get("max_drawdown"),
        "trade_count": final_metrics.get("trade_count"),
        "turnover": final_metrics.get("turnover"),
    }


def build_artifact_trace(run_dir: Path | str) -> pd.DataFrame:
    run_dir = Path(run_dir)
    rows = [
        ("ML demo summary", run_dir / "ml_demo_summary.json"),
        ("Predictions", run_dir / "model" / "predictions.csv"),
        ("ML signal", run_dir / "signal" / "ml_signal.csv"),
        ("Research-validation summary", run_dir / RESEARCH_SUMMARY_RELATIVE),
        ("Final-holdout metrics", run_dir / FINAL_HOLDOUT_RELATIVE / "metrics_summary.json"),
        ("Final-holdout equity curve", run_dir / FINAL_HOLDOUT_RELATIVE / "equity_curve.csv"),
        ("Final-holdout trade log", run_dir / FINAL_HOLDOUT_RELATIVE / "trade_log.csv"),
        ("HTML artifact report", run_dir / "interview_artifact_report.html"),
    ]
    return pd.DataFrame(
        [{"artifact": label, "path": str(path), "exists": path.exists()} for label, path in rows]
    )


def _research_path(research_summary: dict[str, Any] | None, key: str) -> Path | None:
    if research_summary is None:
        return None
    value = research_summary.get("paths", {}).get(key)
    return Path(value) if value else None


def _read_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with open(path) as f:
        payload = json.load(f)
    return payload if isinstance(payload, dict) else None


def _read_csv_optional(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)
