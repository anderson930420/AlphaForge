from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.ml_signal import (
    ML_SIGNAL_SIGNAL_COLUMNS,
    build_classifier_probability_signal,
)


def test_classifier_probability_signal_builds_v02_schema() -> None:
    predictions = pd.DataFrame({
        "asset_id": ["A", "B", "C"],
        "date": ["2024-01-15", "2024-01-15", "2024-01-15"],
        "predicted_probability": [0.7, 0.5, 0.2],
    })

    result = build_classifier_probability_signal(
        predictions,
        long_probability_threshold=0.6,
        short_probability_threshold=0.4,
    )

    assert list(result.columns) == list(ML_SIGNAL_SIGNAL_COLUMNS)
    assert len(result) == 3
    assert set(result["direction"]) == {-1, 0, 1}
    assert str(result.loc[0, "datetime"])[:10] == "2024-01-31"
    assert str(result.loc[0, "available_at"])[:10] == "2024-01-31"


def test_classifier_probability_signal_normalizes_weights_per_date() -> None:
    predictions = pd.DataFrame({
        "asset_id": ["A", "B", "C", "D"],
        "date": ["2024-01-31"] * 4,
        "predicted_probability": [0.9, 0.8, 0.2, 0.1],
    })

    result = build_classifier_probability_signal(
        predictions,
        long_probability_threshold=0.6,
        short_probability_threshold=0.4,
        gross_long_weight=1.0,
        gross_short_weight=-1.0,
    )

    longs = result[result["direction"] == 1]
    shorts = result[result["direction"] == -1]
    assert len(longs) == 2
    assert len(shorts) == 2
    assert abs(longs["target_weight"].sum() - 1.0) < 1e-9
    assert abs(shorts["target_weight"].sum() - (-1.0)) < 1e-9
    assert set(longs["target_weight"]) == {0.5}
    assert set(shorts["target_weight"]) == {-0.5}


def test_classifier_probability_signal_neutral_for_middle_and_nan() -> None:
    predictions = pd.DataFrame({
        "asset_id": ["A", "B", "C"],
        "date": ["2024-01-31"] * 3,
        "predicted_probability": [0.41, 0.59, None],
    })

    result = build_classifier_probability_signal(predictions)

    assert (result["direction"] == 0).all()
    assert (result["target_weight"] == 0.0).all()


def test_classifier_probability_signal_supports_custom_symbol_and_available_at() -> None:
    predictions = pd.DataFrame({
        "asset_id": ["A"],
        "date": ["2024-01-15"],
        "available": ["2024-01-20"],
        "ticker": ["AAA"],
        "prob": [0.8],
    })

    result = build_classifier_probability_signal(
        predictions,
        probability_col="prob",
        symbol_col="ticker",
        available_at_col="available",
        signal_name="classifier_prob",
        source="UnitTest",
    )

    assert result.loc[0, "symbol"] == "AAA"
    assert result.loc[0, "asset_id"] == "A"
    assert result.loc[0, "signal_name"] == "classifier_prob"
    assert result.loc[0, "source"] == "UnitTest"
    assert str(result.loc[0, "available_at"])[:10] == "2024-01-31"


def test_classifier_probability_signal_rejects_bad_thresholds() -> None:
    predictions = pd.DataFrame({
        "asset_id": ["A"],
        "date": ["2024-01-31"],
        "predicted_probability": [0.8],
    })

    with pytest.raises(ValueError, match="long_probability_threshold"):
        build_classifier_probability_signal(predictions, long_probability_threshold=1.1)
    with pytest.raises(ValueError, match="short_probability_threshold"):
        build_classifier_probability_signal(predictions, short_probability_threshold=-0.1)
    with pytest.raises(ValueError, match="must be less than"):
        build_classifier_probability_signal(
            predictions,
            long_probability_threshold=0.4,
            short_probability_threshold=0.6,
        )


def test_classifier_probability_signal_rejects_missing_columns() -> None:
    predictions = pd.DataFrame({"asset_id": ["A"], "date": ["2024-01-31"]})

    with pytest.raises(ValueError, match="Missing required columns"):
        build_classifier_probability_signal(predictions)


def test_build_classifier_signal_script_writes_csv(tmp_path: Path) -> None:
    predictions = pd.DataFrame({
        "asset_id": ["A", "B", "C"],
        "date": ["2024-01-31"] * 3,
        "predicted_probability": [0.8, 0.5, 0.2],
    })
    predictions_path = tmp_path / "predictions.csv"
    output_path = tmp_path / "classifier_signal.csv"
    predictions.to_csv(predictions_path, index=False)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_classifier_signal.py",
            "--predictions",
            str(predictions_path),
            "--output",
            str(output_path),
            "--long-probability-threshold",
            "0.6",
            "--short-probability-threshold",
            "0.4",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    frame = pd.read_csv(output_path)
    assert list(frame.columns) == list(ML_SIGNAL_SIGNAL_COLUMNS)
    assert set(frame["direction"]) == {-1, 0, 1}
    assert "nonzero_target_weight_count" in result.stdout
