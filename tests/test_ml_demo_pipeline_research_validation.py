from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.ml_models import _require_sklearn
from alphaforge.ml_signal import ML_SIGNAL_SIGNAL_COLUMNS


FIXTURES = Path(__file__).resolve().parent / "fixtures"
ML_DEMO_FIXTURES = FIXTURES / "ml_demo_pipeline"
FEATURES_CSV = ML_DEMO_FIXTURES / "features.csv"
RETURNS_CSV = ML_DEMO_FIXTURES / "monthly_returns.csv"
MARKET_DATA_CSV = FIXTURES / "ml_signal_research_validation" / "market_data.csv"
PIPELINE_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_ml_demo_pipeline.py"


def _require_sklearn_test() -> bool:
    try:
        _require_sklearn()
        return True
    except ImportError:
        return False


SKLEARN_AVAILABLE = _require_sklearn_test()


def _base_args(output_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(PIPELINE_SCRIPT),
        "--features",
        str(FEATURES_CSV),
        "--returns",
        str(RETURNS_CSV),
        "--output-dir",
        str(output_dir),
        "--model",
        "ridge_regressor",
        "--feature-cols",
        "Mom12m,BM,Investment",
        "--label-col",
        "ret_fwd_1m",
        "--train-end",
        "2024-03-31",
        "--long-quantile",
        "0.8",
        "--short-quantile",
        "0.2",
        "--diagnostic-quantiles",
        "2",
    ]


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_ml_demo_pipeline_optional_research_validation_writes_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "pipeline_out"
    result = _run(
        _base_args(output_dir)
        + [
            "--run-research-validation",
            "--research-validation-market-data",
            str(MARKET_DATA_CSV),
            "--research-validation-symbol",
            "A",
            "--research-validation-development-start",
            "2024-01-31",
            "--research-validation-development-end",
            "2024-03-31",
            "--research-validation-holdout-start",
            "2024-04-30",
            "--research-validation-holdout-end",
            "2024-06-30",
            "--research-validation-train-size",
            "2",
            "--research-validation-test-size",
            "1",
            "--research-validation-step-size",
            "1",
        ]
    )

    assert result.returncode == 0, result.stderr
    research_root = output_dir / "research_validation"
    summary_path = research_root / "ml_demo_research_validation_summary.json"
    derived_signal_path = research_root / "derived_signal" / "single_symbol_signal.csv"
    protocol_summary_path = research_root / "ml_signal_single_symbol_validation" / "research_protocol_summary.json"

    assert summary_path.exists()
    assert derived_signal_path.exists()
    assert protocol_summary_path.exists()

    signal = pd.read_csv(derived_signal_path)
    assert list(signal.columns) == list(ML_SIGNAL_SIGNAL_COLUMNS)
    assert set(signal["symbol"]) == {"A"}

    with open(summary_path) as f:
        research_summary = json.load(f)
    assert research_summary["status"] == "ok"
    assert research_summary["validation_mode"] == "single_symbol_projection"
    assert research_summary["does_train_model"] is False
    assert research_summary["does_generate_predictions"] is False
    assert research_summary["does_add_multi_symbol_backtest"] is False
    assert research_summary["does_execute_live_trades"] is False
    assert research_summary["paths"]["derived_single_symbol_signal"] == str(derived_signal_path)
    assert research_summary["paths"]["research_protocol_summary"] == str(protocol_summary_path)

    with open(output_dir / "ml_demo_summary.json") as f:
        demo_summary = json.load(f)
    assert demo_summary["does_run_research_validation"] is True
    assert demo_summary["paths"]["research_validation_summary"] == str(summary_path)
    assert demo_summary["research_validation"]["paths"]["summary"] == str(summary_path)
    assert "multi-symbol portfolio validation" in demo_summary["boundary_note"]


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_ml_demo_pipeline_research_validation_requires_explicit_inputs(tmp_path: Path) -> None:
    output_dir = tmp_path / "pipeline_out"
    result = _run(_base_args(output_dir) + ["--run-research-validation"])

    assert result.returncode != 0
    assert "--run-research-validation requires" in result.stderr
    assert "--research-validation-market-data" in result.stderr
    assert "--research-validation-symbol" in result.stderr
