from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from alphaforge.dashboard_ml_predictions import (
    ML_PREDICTION_DIAGNOSTIC_ARTIFACTS,
    load_ml_prediction_diagnostics_artifacts,
    ml_prediction_diagnostic_step_statuses,
)


def _write_ml_prediction_diagnostics(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "ml_prediction_summary.json").write_text(json.dumps({
        "prediction_col": "predicted_return",
        "label_col": "ret_fwd_1m",
        "row_count": 240,
        "date_count": 12,
        "asset_count": 20,
        "quantiles": 5,
        "prediction_ic_mean": 0.12,
        "prediction_rank_ic_mean": 0.10,
        "long_short_spread_mean": 0.01,
        "overall_mae": 0.02,
    }))
    pd.DataFrame({
        "date": ["2020-01-31", "2020-02-29"],
        "row_count": [20, 20],
        "prediction_ic": [0.10, 0.15],
        "prediction_rank_ic": [0.08, 0.12],
    }).to_csv(root / "ml_prediction_ic_timeseries.csv", index=False)
    pd.DataFrame({
        "date": ["2020-01-31", "2020-01-31"],
        "quantile": ["Q1", "Q5"],
        "quantile_number": [1, 5],
        "asset_count": [4, 4],
        "mean_forward_return": [0.01, 0.03],
        "median_forward_return": [0.01, 0.03],
        "mean_prediction": [0.00, 0.04],
    }).to_csv(root / "ml_prediction_quantile_returns.csv", index=False)
    pd.DataFrame({
        "date": ["2020-01-31", "2020-02-29"],
        "long_quantile": ["Q5", "Q5"],
        "short_quantile": ["Q1", "Q1"],
        "long_short_spread": [0.02, 0.03],
    }).to_csv(root / "ml_prediction_long_short_spread.csv", index=False)
    pd.DataFrame({
        "date": ["2020-01-31", "2020-02-29"],
        "row_count": [20, 20],
        "mse": [0.001, 0.002],
        "mae": [0.02, 0.03],
        "mean_error": [0.001, -0.001],
        "mean_prediction": [0.01, 0.02],
        "mean_label": [0.009, 0.021],
    }).to_csv(root / "ml_prediction_error_by_date.csv", index=False)


class TestMLPredictionDashboardArtifacts:
    def test_load_ml_prediction_diagnostics_artifacts_reports_complete_bundle(self, tmp_path: Path):
        _write_ml_prediction_diagnostics(tmp_path)

        bundle = load_ml_prediction_diagnostics_artifacts(tmp_path)

        assert bundle.is_complete
        assert bundle.has_any_artifacts
        assert bundle.expected_files == ML_PREDICTION_DIAGNOSTIC_ARTIFACTS
        assert set(bundle.present_files) == set(ML_PREDICTION_DIAGNOSTIC_ARTIFACTS)
        assert bundle.missing_files == ()
        assert bundle.summary is not None
        assert bundle.summary["prediction_col"] == "predicted_return"

    def test_load_ml_prediction_diagnostics_artifacts_reports_missing_files(self, tmp_path: Path):
        (tmp_path / "ml_prediction_summary.json").write_text(json.dumps({"prediction_col": "predicted_return"}))

        bundle = load_ml_prediction_diagnostics_artifacts(tmp_path)

        assert not bundle.is_complete
        assert bundle.has_any_artifacts
        assert "ml_prediction_summary.json" in bundle.present_files
        assert "ml_prediction_ic_timeseries.csv" in bundle.missing_files
        assert bundle.summary == {"prediction_col": "predicted_return"}

    def test_ml_prediction_table_summaries_include_shape_and_preview(self, tmp_path: Path):
        _write_ml_prediction_diagnostics(tmp_path)

        bundle = load_ml_prediction_diagnostics_artifacts(tmp_path, preview_rows=1)
        ic = bundle.table_summaries["ic_timeseries"]

        assert ic.exists
        assert ic.row_count == 2
        assert ic.column_count == 4
        assert ic.columns == ("date", "row_count", "prediction_ic", "prediction_rank_ic")
        assert len(ic.preview_rows) == 1

    def test_ml_prediction_diagnostic_step_statuses_are_ordered(self, tmp_path: Path):
        _write_ml_prediction_diagnostics(tmp_path)

        bundle = load_ml_prediction_diagnostics_artifacts(tmp_path)
        steps = ml_prediction_diagnostic_step_statuses(bundle)

        assert [step["artifact"] for step in steps] == list(ML_PREDICTION_DIAGNOSTIC_ARTIFACTS)
        assert all(step["status"] == "present" for step in steps)
        assert steps[0]["stage"] == "Summary statistics"
