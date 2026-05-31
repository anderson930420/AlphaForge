from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd


FIXTURES = Path(__file__).resolve().parent / "fixtures"
PREDICTIONS = FIXTURES / "classifier_signal_research_validation" / "predictions.csv"
MARKET_DATA = FIXTURES / "ml_signal_research_validation" / "market_data.csv"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_classifier_signal_research_validation_demo.py"


def test_classifier_signal_research_validation_demo_writes_showcase_compatible_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "classifier_demo"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--predictions",
            str(PREDICTIONS),
            "--market-data",
            str(MARKET_DATA),
            "--symbol",
            "C",
            "--output-dir",
            str(output_dir),
            "--development-start",
            "2024-01-31",
            "--development-end",
            "2024-03-31",
            "--holdout-start",
            "2024-04-30",
            "--holdout-end",
            "2024-06-30",
            "--train-size",
            "2",
            "--test-size",
            "1",
            "--step-size",
            "1",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode == 0, result.stderr

    demo_summary_path = output_dir / "ml_demo_summary.json"
    research_summary_path = output_dir / "research_validation" / "ml_demo_research_validation_summary.json"
    signal_path = output_dir / "signal" / "ml_signal.csv"
    derived_signal_path = output_dir / "research_validation" / "derived_signal" / "single_symbol_signal.csv"
    final_holdout = output_dir / "research_validation" / "ml_signal_single_symbol_validation" / "final_holdout"

    assert demo_summary_path.exists()
    assert research_summary_path.exists()
    assert signal_path.exists()
    assert derived_signal_path.exists()
    assert (final_holdout / "metrics_summary.json").exists()
    assert (final_holdout / "equity_curve.csv").exists()
    assert (final_holdout / "trade_log.csv").exists()

    with open(demo_summary_path) as f:
        demo_summary = json.load(f)
    with open(research_summary_path) as f:
        research_summary = json.load(f)

    assert demo_summary["stage"] == "classifier_signal_research_validation_demo"
    assert demo_summary["does_run_research_validation"] is True
    assert demo_summary["model"] == "classifier_probability_signal"
    assert research_summary["symbol"] == "C"
    assert research_summary["nonzero_target_weight_count"] > 0
    assert research_summary["all_flat_selected_symbol"] is False
    assert research_summary["date_alignment"]["extra_signal_dates"] == []
    assert research_summary["warnings"] == []

    signal = pd.read_csv(signal_path)
    derived_signal = pd.read_csv(derived_signal_path)
    assert set(signal["signal_name"]) == {"ml_predicted_probability"}
    assert set(derived_signal["symbol"]) == {"C"}
    assert (derived_signal["target_weight"].abs() > 0).all()


def test_classifier_signal_research_validation_demo_rejects_missing_market_alignment(tmp_path: Path) -> None:
    predictions = pd.DataFrame({
        "asset_id": ["C"],
        "date": ["2024-07-31"],
        "predicted_probability": [0.8],
    })
    predictions_path = tmp_path / "predictions.csv"
    predictions.to_csv(predictions_path, index=False)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--predictions",
            str(predictions_path),
            "--market-data",
            str(MARKET_DATA),
            "--symbol",
            "C",
            "--output-dir",
            str(tmp_path / "bad_demo"),
            "--development-start",
            "2024-01-31",
            "--development-end",
            "2024-03-31",
            "--holdout-start",
            "2024-04-30",
            "--holdout-end",
            "2024-06-30",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode != 0
    assert "dates not present in market_data" in result.stderr
