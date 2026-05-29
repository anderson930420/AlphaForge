from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.ml_demo_artifacts import (
    build_synthetic_prediction_demo,
    write_synthetic_prediction_demo_artifacts,
)


class TestSyntheticPredictionDemo:
    def test_build_synthetic_prediction_demo_shape_and_columns(self):
        frame = build_synthetic_prediction_demo(months=12, assets=20)

        assert len(frame) == 240
        assert set(frame.columns) == {
            "asset_id",
            "date",
            "predicted_return",
            "ret_fwd_1m",
            "source",
        }
        assert frame["date"].nunique() == 12
        assert frame["asset_id"].nunique() == 20
        assert frame.groupby("date")["asset_id"].nunique().eq(20).all()

    def test_build_synthetic_prediction_demo_has_cross_sectional_dispersion(self):
        frame = build_synthetic_prediction_demo(months=3, assets=10)

        assert frame.groupby("date")["predicted_return"].nunique().ge(2).all()
        assert frame.groupby("date")["ret_fwd_1m"].nunique().ge(2).all()

    def test_build_synthetic_prediction_demo_rejects_invalid_shape(self):
        with pytest.raises(ValueError, match="months"):
            build_synthetic_prediction_demo(months=0, assets=20)
        with pytest.raises(ValueError, match="assets"):
            build_synthetic_prediction_demo(months=12, assets=1)

    def test_write_synthetic_prediction_demo_artifacts_outputs_non_empty_diagnostics(self, tmp_path: Path):
        paths = write_synthetic_prediction_demo_artifacts(tmp_path, months=12, assets=20, quantiles=5)

        predictions = pd.read_csv(paths["predictions"])
        assert len(predictions) == 240

        diagnostics_dir = Path(paths["diagnostics_dir"])
        with open(diagnostics_dir / "ml_prediction_summary.json") as f:
            summary = json.load(f)

        assert summary["row_count"] == 240
        assert summary["date_count"] == 12
        assert summary["asset_count"] == 20
        assert summary["prediction_ic_observation_count"] == 12
        assert summary["prediction_rank_ic_observation_count"] == 12
        assert summary["long_short_observation_count"] == 12
        assert summary["long_short_spread_mean"] is not None

        ic = pd.read_csv(diagnostics_dir / "ml_prediction_ic_timeseries.csv")
        quantile_returns = pd.read_csv(diagnostics_dir / "ml_prediction_quantile_returns.csv")
        spread = pd.read_csv(diagnostics_dir / "ml_prediction_long_short_spread.csv")
        errors = pd.read_csv(diagnostics_dir / "ml_prediction_error_by_date.csv")

        assert len(ic) == 12
        assert len(quantile_returns) == 60
        assert len(spread) == 12
        assert len(errors) == 12

    def test_run_synthetic_prediction_demo_script_writes_outputs(self, tmp_path: Path):
        output_dir = tmp_path / "synthetic_prediction_demo"

        result = subprocess.run(
            [
                sys.executable,
                "scripts/run_synthetic_prediction_demo.py",
                "--output-dir", str(output_dir),
                "--months", "6",
                "--assets", "10",
                "--quantiles", "5",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": "src"},
        )

        assert result.returncode == 0, f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
        payload = json.loads(result.stdout)
        assert payload["status"] == "ok"
        assert (output_dir / "predictions.csv").exists()
        assert (output_dir / "synthetic_prediction_demo_summary.json").exists()
        assert (output_dir / "ml_prediction_diagnostics" / "ml_prediction_summary.json").exists()
