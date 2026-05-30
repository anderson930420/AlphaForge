from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.ml_signal import ML_SIGNAL_SIGNAL_COLUMNS, build_single_asset_threshold_signal


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "single_asset_ml_signal"
PREDICTIONS_CSV = FIXTURES / "predictions.csv"
MULTI_ASSET_PREDICTIONS_CSV = FIXTURES / "multi_asset_predictions.csv"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_single_asset_ml_signal.py"


def test_build_single_asset_threshold_signal_maps_long_short_flat() -> None:
    predictions = pd.read_csv(PREDICTIONS_CSV)

    signal = build_single_asset_threshold_signal(
        predictions,
        asset_id="A",
        long_threshold=0.01,
        short_threshold=-0.01,
    )

    assert list(signal.columns) == list(ML_SIGNAL_SIGNAL_COLUMNS)
    assert signal["direction"].tolist() == [1, -1, 0, 1, 0]
    assert signal["target_weight"].tolist() == [1.0, -1.0, 0.0, 1.0, 0.0]
    assert set(signal["symbol"]) == {"A"}
    assert set(signal["asset_id"]) == {"A"}


def test_build_single_asset_threshold_signal_requires_asset_for_multi_asset_panel() -> None:
    predictions = pd.read_csv(MULTI_ASSET_PREDICTIONS_CSV)

    with pytest.raises(ValueError, match="Prediction panel contains multiple asset_id values"):
        build_single_asset_threshold_signal(predictions)


def test_build_single_asset_threshold_signal_selects_requested_asset() -> None:
    predictions = pd.read_csv(MULTI_ASSET_PREDICTIONS_CSV)

    signal = build_single_asset_threshold_signal(
        predictions,
        asset_id="B",
        long_threshold=0.0,
        short_threshold=0.0,
    )

    assert set(signal["asset_id"]) == {"B"}
    assert signal["direction"].tolist() == [-1, 1]


def test_build_single_asset_threshold_signal_validates_threshold_order() -> None:
    predictions = pd.read_csv(PREDICTIONS_CSV)

    with pytest.raises(ValueError, match="short_threshold must be less than or equal to long_threshold"):
        build_single_asset_threshold_signal(
            predictions,
            asset_id="A",
            long_threshold=-0.01,
            short_threshold=0.01,
        )


def test_run_single_asset_ml_signal_script_writes_signal_and_summary(tmp_path: Path) -> None:
    output = tmp_path / "signal.csv"
    summary = tmp_path / "summary.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--predictions",
            str(PREDICTIONS_CSV),
            "--output",
            str(output),
            "--summary-output",
            str(summary),
            "--asset-id",
            "A",
            "--long-threshold",
            "0.01",
            "--short-threshold",
            "-0.01",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode == 0, result.stderr
    signal = pd.read_csv(output)
    assert list(signal.columns) == list(ML_SIGNAL_SIGNAL_COLUMNS)
    assert signal["direction"].tolist() == [1, -1, 0, 1, 0]

    with open(summary) as f:
        payload = json.load(f)
    assert payload["status"] == "ok"
    assert payload["stage"] == "single_asset_ml_threshold_signal"
    assert payload["nonzero_target_weight_count"] == 3
    assert payload["all_flat_signal"] is False
    assert payload["does_run_research_validation"] is False


def test_run_single_asset_ml_signal_script_requires_asset_for_multi_asset_panel(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--predictions",
            str(MULTI_ASSET_PREDICTIONS_CSV),
            "--output",
            str(tmp_path / "signal.csv"),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode != 0
    assert "Prediction panel contains multiple asset_id values" in result.stderr
