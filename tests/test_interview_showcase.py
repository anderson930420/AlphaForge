from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from alphaforge.interview_showcase import (
    build_artifact_trace,
    build_health_checks,
    extract_overview_metrics,
    load_interview_showcase_artifacts,
    summarize_signal_exposure,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f)


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def test_interview_showcase_loads_artifacts_and_health_checks(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_json(run_dir / "ml_demo_summary.json", {
        "model": "ridge_regressor",
        "predictions_rows": 6,
        "ml_signal_rows": 6,
        "does_run_research_validation": True,
    })
    _write_json(run_dir / "research_validation" / "ml_demo_research_validation_summary.json", {
        "symbol": "C",
        "selected_signal_row_count": 2,
        "nonzero_target_weight_count": 2,
        "all_flat_selected_symbol": False,
        "date_alignment": {"extra_signal_dates": []},
        "warnings": [],
        "paths": {
            "derived_single_symbol_signal": str(
                run_dir / "research_validation" / "derived_signal" / "single_symbol_signal.csv"
            )
        },
    })
    _write_json(
        run_dir / "research_validation" / "ml_signal_single_symbol_validation" / "final_holdout" / "metrics_summary.json",
        {
            "total_return": 0.01,
            "sharpe_ratio": 1.2,
            "max_drawdown": -0.02,
            "trade_count": 1,
            "turnover": 1.0,
        },
    )
    _write_csv(run_dir / "signal" / "ml_signal.csv", pd.DataFrame({
        "datetime": ["2024-04-30", "2024-04-30"],
        "symbol": ["A", "C"],
        "target_weight": [0.0, 1.0],
    }))
    _write_csv(run_dir / "research_validation" / "derived_signal" / "single_symbol_signal.csv", pd.DataFrame({
        "datetime": ["2024-04-30"],
        "symbol": ["C"],
        "target_weight": [1.0],
    }))
    _write_csv(run_dir / "model" / "predictions.csv", pd.DataFrame({
        "asset_id": ["C"],
        "date": ["2024-04-30"],
        "predicted_return": [0.02],
        "ret_fwd_1m": [0.01],
    }))
    _write_csv(
        run_dir / "research_validation" / "ml_signal_single_symbol_validation" / "final_holdout" / "equity_curve.csv",
        pd.DataFrame({"datetime": ["2024-04-30"], "equity": [101000.0]}),
    )
    _write_csv(
        run_dir / "research_validation" / "ml_signal_single_symbol_validation" / "final_holdout" / "trade_log.csv",
        pd.DataFrame({"datetime": ["2024-04-30"], "trade": [1.0]}),
    )

    artifacts = load_interview_showcase_artifacts(run_dir)
    checks = build_health_checks(artifacts.research_summary)
    overview = extract_overview_metrics(artifacts)
    exposure = summarize_signal_exposure(artifacts.signal)
    trace = build_artifact_trace(run_dir)

    assert artifacts.ml_demo_summary is not None
    assert artifacts.research_summary is not None
    assert artifacts.signal is not None
    assert artifacts.derived_signal is not None
    assert artifacts.predictions is not None
    assert artifacts.equity_curve is not None
    assert artifacts.trade_log is not None
    assert all(check["status"] == "pass" for check in checks)
    assert overview["model"] == "ridge_regressor"
    assert overview["symbol"] == "C"
    assert overview["nonzero_target_weight_count"] == 2
    assert exposure.loc[exposure["symbol"] == "C", "nonzero_target_weight_count"].iloc[0] == 1
    assert set(trace["artifact"]) >= {"ML demo summary", "HTML artifact report"}


def test_interview_showcase_health_checks_fail_without_research_summary() -> None:
    checks = build_health_checks(None)

    assert checks == [{"check": "research summary exists", "status": "fail", "value": "missing"}]


def test_summarize_signal_exposure_handles_missing_signal() -> None:
    exposure = summarize_signal_exposure(None)

    assert list(exposure.columns) == ["symbol", "rows", "nonzero_target_weight_count", "total_abs_weight"]
    assert exposure.empty
