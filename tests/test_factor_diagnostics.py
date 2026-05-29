from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.factor_diagnostics import (
    build_ic_by_date,
    build_quantile_returns,
    load_supervised_panel,
    run_factor_diagnostics,
    write_factor_diagnostics,
)


def _panel() -> pd.DataFrame:
    return pd.DataFrame({
        "asset_id": ["A", "B", "C", "D", "A", "B", "C", "D"],
        "date": [
            "2024-01-15", "2024-01-20", "2024-01-25", "2024-01-30",
            "2024-02-15", "2024-02-20", "2024-02-25", "2024-02-28",
        ],
        "Mom12m": [0.10, 0.20, 0.30, 0.40, 0.11, 0.21, 0.31, 0.41],
        "ret_fwd_1m": [0.01, 0.02, 0.03, 0.04, 0.015, 0.025, 0.035, 0.045],
    })


class TestRunFactorDiagnostics:
    def test_summary_contains_core_metrics(self):
        result = run_factor_diagnostics(_panel(), factor_col="Mom12m", quantiles=2)

        assert result.summary["factor_col"] == "Mom12m"
        assert result.summary["label_col"] == "ret_fwd_1m"
        assert result.summary["row_count"] == 8
        assert result.summary["date_count"] == 2
        assert result.summary["asset_count"] == 4
        assert result.summary["mean_coverage_ratio"] == 1.0
        assert result.summary["ic_observation_count"] == 2
        assert result.summary["rank_ic_observation_count"] == 2
        assert result.summary["long_short_observation_count"] == 2

    def test_coverage_by_date_counts_missing_factor_values(self):
        panel = _panel()
        panel.loc[0, "Mom12m"] = None

        result = run_factor_diagnostics(panel, factor_col="Mom12m", quantiles=2)
        first = result.coverage_by_date.iloc[0]

        assert first["asset_count"] == 4
        assert first["valid_factor_count"] == 3
        assert first["missing_factor_count"] == 1
        assert first["coverage_ratio"] == 0.75

    def test_distribution_by_date_has_expected_columns(self):
        result = run_factor_diagnostics(_panel(), factor_col="Mom12m", quantiles=2)

        required = {"date", "count", "mean", "std", "min", "median", "max"}
        assert required.issubset(result.distribution_by_date.columns)
        assert len(result.distribution_by_date) == 2

    def test_ic_and_rank_ic_are_computed_by_date(self):
        result = run_factor_diagnostics(_panel(), factor_col="Mom12m", quantiles=2)

        assert len(result.ic_by_date) == 2
        assert set(result.ic_by_date.columns) == {"date", "row_count", "ic", "rank_ic"}
        assert result.ic_by_date["ic"].notna().all()
        assert result.ic_by_date["rank_ic"].notna().all()

    def test_quantile_returns_and_long_short_spread(self):
        result = run_factor_diagnostics(_panel(), factor_col="Mom12m", quantiles=2)

        assert len(result.quantile_returns) == 4
        assert set(result.quantile_returns["quantile"]) == {"Q1", "Q2"}
        assert len(result.long_short_spread) == 2
        assert (result.long_short_spread["long_short_spread"] > 0).all()

    def test_constant_factor_skips_quantile_returns_and_ic(self):
        panel = _panel()
        panel["Mom12m"] = 1.0

        result = run_factor_diagnostics(panel, factor_col="Mom12m", quantiles=2)

        assert result.ic_by_date["ic"].isna().all()
        assert result.ic_by_date["rank_ic"].isna().all()
        assert result.quantile_returns.empty
        assert result.long_short_spread.empty

    def test_missing_required_columns_raises(self):
        with pytest.raises(ValueError, match="Missing required columns"):
            run_factor_diagnostics(pd.DataFrame({"asset_id": ["A"]}), factor_col="Mom12m")

    def test_quantiles_must_be_at_least_two(self):
        with pytest.raises(ValueError, match="quantiles"):
            run_factor_diagnostics(_panel(), factor_col="Mom12m", quantiles=1)

    def test_custom_column_names_work(self):
        panel = pd.DataFrame({
            "permno": ["A", "B", "C", "D"],
            "yyyymm": ["2024-01-31"] * 4,
            "factor": [1, 2, 3, 4],
            "label": [0.01, 0.02, 0.03, 0.04],
        })

        result = run_factor_diagnostics(
            panel,
            factor_col="factor",
            label_col="label",
            asset_id_col="permno",
            date_col="yyyymm",
            quantiles=2,
        )

        assert result.summary["asset_id_col"] == "permno"
        assert result.summary["date_col"] == "yyyymm"
        assert result.summary["row_count"] == 4


class TestHelpers:
    def test_build_ic_by_date_handles_too_few_rows(self):
        frame = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-31"]),
            "factor": [1.0],
            "label": [0.01],
        })

        result = build_ic_by_date(frame, factor_col="factor", label_col="label", date_col="date")

        assert result.iloc[0]["row_count"] == 1
        assert pd.isna(result.iloc[0]["ic"])
        assert pd.isna(result.iloc[0]["rank_ic"])

    def test_build_quantile_returns_skips_thin_dates(self):
        frame = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-31", "2024-01-31"]),
            "factor": [1.0, 2.0],
            "label": [0.01, 0.02],
        })

        result = build_quantile_returns(frame, factor_col="factor", label_col="label", date_col="date", quantiles=5)

        assert result.empty

    def test_load_supervised_panel_supports_csv(self, tmp_path: Path):
        path = tmp_path / "panel.csv"
        _panel().to_csv(path, index=False)

        loaded = load_supervised_panel(path)

        assert len(loaded) == 8
        assert "Mom12m" in loaded.columns

    def test_load_supervised_panel_rejects_unknown_suffix(self):
        with pytest.raises(ValueError, match="Unsupported supervised panel suffix"):
            load_supervised_panel(Path("panel.xlsx"))

    def test_write_factor_diagnostics_outputs_all_artifacts(self, tmp_path: Path):
        result = run_factor_diagnostics(_panel(), factor_col="Mom12m", quantiles=2)

        paths = write_factor_diagnostics(result, tmp_path)

        expected = {
            "factor_summary",
            "factor_coverage_by_date",
            "factor_distribution_by_date",
            "factor_ic_timeseries",
            "factor_quantile_returns",
            "factor_long_short_spread",
        }
        assert set(paths) == expected
        for path in paths.values():
            assert Path(path).exists()
        with open(paths["factor_summary"]) as f:
            summary = json.load(f)
        assert summary["factor_col"] == "Mom12m"


class TestScript:
    def test_run_factor_diagnostics_script_writes_outputs(self, tmp_path: Path):
        panel = tmp_path / "panel.csv"
        output_dir = tmp_path / "factor_diagnostics"
        _panel().to_csv(panel, index=False)

        result = subprocess.run(
            [
                sys.executable,
                "scripts/run_factor_diagnostics.py",
                "--panel", str(panel),
                "--output-dir", str(output_dir),
                "--factor-col", "Mom12m",
                "--quantiles", "2",
            ],
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "PYTHONPATH": "src"},
        )

        assert result.returncode == 0, f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
        payload = json.loads(result.stdout)
        assert payload["status"] == "ok"
        assert (output_dir / "factor_summary.json").exists()
        assert (output_dir / "factor_ic_timeseries.csv").exists()
        assert (output_dir / "factor_quantile_returns.csv").exists()
