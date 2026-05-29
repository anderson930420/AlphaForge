from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from alphaforge.dashboard_artifacts import (
    FACTOR_DIAGNOSTIC_ARTIFACTS,
    factor_diagnostic_step_statuses,
    load_factor_diagnostics_artifacts,
)


def _write_factor_diagnostics(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "factor_summary.json").write_text(json.dumps({
        "factor_col": "Mom12m",
        "label_col": "ret_fwd_1m",
        "row_count": 4,
        "date_count": 2,
        "asset_count": 2,
        "mean_coverage_ratio": 1.0,
        "ic_mean": 0.75,
        "rank_ic_mean": 0.5,
        "long_short_spread_mean": 0.0125,
    }))
    pd.DataFrame({
        "date": ["2024-01-31", "2024-02-29"],
        "asset_count": [2, 2],
        "valid_factor_count": [2, 2],
        "missing_factor_count": [0, 0],
        "coverage_ratio": [1.0, 1.0],
    }).to_csv(root / "factor_coverage_by_date.csv", index=False)
    pd.DataFrame({
        "date": ["2024-01-31", "2024-02-29"],
        "count": [2, 2],
        "mean": [0.1, 0.2],
        "std": [0.01, 0.02],
        "min": [0.09, 0.18],
        "median": [0.1, 0.2],
        "max": [0.11, 0.22],
    }).to_csv(root / "factor_distribution_by_date.csv", index=False)
    pd.DataFrame({
        "date": ["2024-01-31", "2024-02-29"],
        "row_count": [2, 2],
        "ic": [1.0, 0.5],
        "rank_ic": [1.0, 0.0],
    }).to_csv(root / "factor_ic_timeseries.csv", index=False)
    pd.DataFrame({
        "date": ["2024-01-31", "2024-01-31"],
        "quantile": ["Q1", "Q2"],
        "quantile_number": [1, 2],
        "asset_count": [1, 1],
        "mean_forward_return": [0.01, 0.02],
        "median_forward_return": [0.01, 0.02],
    }).to_csv(root / "factor_quantile_returns.csv", index=False)
    pd.DataFrame({
        "date": ["2024-01-31"],
        "long_quantile": ["Q2"],
        "short_quantile": ["Q1"],
        "long_short_spread": [0.01],
    }).to_csv(root / "factor_long_short_spread.csv", index=False)


class TestFactorDiagnosticsDashboardArtifacts:
    def test_load_factor_diagnostics_artifacts_reports_complete_bundle(self, tmp_path: Path):
        _write_factor_diagnostics(tmp_path)

        bundle = load_factor_diagnostics_artifacts(tmp_path)

        assert bundle.is_complete
        assert bundle.has_any_artifacts
        assert bundle.expected_files == FACTOR_DIAGNOSTIC_ARTIFACTS
        assert set(bundle.present_files) == set(FACTOR_DIAGNOSTIC_ARTIFACTS)
        assert bundle.missing_files == ()
        assert bundle.summary is not None
        assert bundle.summary["factor_col"] == "Mom12m"

    def test_load_factor_diagnostics_artifacts_reports_missing_files(self, tmp_path: Path):
        (tmp_path / "factor_summary.json").write_text(json.dumps({"factor_col": "Mom12m"}))

        bundle = load_factor_diagnostics_artifacts(tmp_path)

        assert not bundle.is_complete
        assert bundle.has_any_artifacts
        assert "factor_summary.json" in bundle.present_files
        assert "factor_ic_timeseries.csv" in bundle.missing_files
        assert bundle.summary == {"factor_col": "Mom12m"}

    def test_factor_diagnostic_table_summaries_include_shape_and_preview(self, tmp_path: Path):
        _write_factor_diagnostics(tmp_path)

        bundle = load_factor_diagnostics_artifacts(tmp_path, preview_rows=1)
        ic = bundle.table_summaries["ic_timeseries"]

        assert ic.exists
        assert ic.row_count == 2
        assert ic.column_count == 4
        assert ic.columns == ("date", "row_count", "ic", "rank_ic")
        assert len(ic.preview_rows) == 1

    def test_factor_diagnostic_step_statuses_are_ordered(self, tmp_path: Path):
        _write_factor_diagnostics(tmp_path)

        bundle = load_factor_diagnostics_artifacts(tmp_path)
        steps = factor_diagnostic_step_statuses(bundle)

        assert [step["artifact"] for step in steps] == list(FACTOR_DIAGNOSTIC_ARTIFACTS)
        assert all(step["status"] == "present" for step in steps)
        assert steps[0]["stage"] == "Summary statistics"
