from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.crsp_ml_e2e_report import (
    build_crsp_ml_e2e_report_payload,
    load_crsp_ml_e2e_artifacts,
    render_crsp_ml_e2e_report_html,
    render_crsp_ml_e2e_report_markdown,
    write_crsp_ml_e2e_report,
)
from alphaforge.json_utils import write_json_artifact


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_crsp_ml_e2e_report.py"


def _make_portfolio_returns() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2021-01-31", "2021-02-28", "2021-03-31"]),
            "long_ret": [0.02, 0.01, 0.04],
            "short_ret": [0.01, 0.03, 0.01],
            "long_short_ret": [0.01, -0.02, 0.03],
            "long_count": [1, 1, 1],
            "short_count": [1, 1, 1],
            "quantile": [0.1, 0.1, 0.1],
        }
    )


def _make_e2e_artifacts(root: Path) -> Path:
    e2e_dir = root / "crsp_ml_e2e"
    dataset_dir = e2e_dir / "dataset"
    walkforward_dir = e2e_dir / "walkforward"
    sklearn_dir = e2e_dir / "sklearn_baseline"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    walkforward_dir.mkdir(parents=True, exist_ok=True)
    sklearn_dir.mkdir(parents=True, exist_ok=True)

    write_json_artifact(
        e2e_dir / "e2e_summary.json",
        {
            "status": "ok",
            "stage": "crsp_ml_e2e_pipeline",
            "monthly_input": "/input/crsp_monthly.parquet",
            "output_dir": str(e2e_dir),
            "dataset_rows": 6,
            "dataset_assets": 2,
            "dataset_date_min": "2020-01-31",
            "dataset_date_max": "2020-03-31",
            "walkforward_windows": 2,
            "first_window_id": "train_2020_test_2021",
            "last_window_id": "train_2021_test_2022",
            "prediction_rows": 4,
            "prediction_date_min": "2021-01-31",
            "prediction_date_max": "2022-12-31",
            "model_name": "ridge",
            "train_years": 10,
            "test_years": 1,
            "step_years": 1,
            "quantile": 0.1,
            "random_state": 0,
            "created_at": "2026-06-02T00:00:00+00:00",
        },
    )
    write_json_artifact(
        dataset_dir / "crsp_ml_dataset_qc.json",
        {
            "status": "ok",
            "rows": 6,
            "assets": 2,
            "months": 3,
            "date_min": "2020-01-31",
            "date_max": "2020-03-31",
            "missing_label_ratio": 0.1667,
            "duplicate_asset_date_rows": 0,
            "feature_columns": [
                "mom12_1",
                "mom6_1",
                "mom3_1",
                "ret1_0",
                "volatility_12m",
                "turnover",
                "log_market_cap",
                "log_price",
            ],
            "label_column": "forward_1m_total_ret",
            "frequency": "monthly",
        },
    )
    write_json_artifact(
        walkforward_dir / "walk_forward_qc.json",
        {
            "status": "ok",
            "windows": 2,
            "total_train_rows": 4,
            "total_test_rows": 2,
            "first_train_start": "2020-01-31",
            "last_test_end": "2022-12-31",
            "train_years": 10,
            "test_years": 1,
            "step_years": 1,
            "per_window": [
                {
                    "window_id": "train_2020_test_2021",
                    "train_start": "2020-01-31",
                    "train_end": "2020-12-31",
                    "test_start": "2021-01-31",
                    "test_end": "2021-12-31",
                    "train_rows": 2,
                    "test_rows": 1,
                    "train_assets": 1,
                    "test_assets": 1,
                    "train_months": 12,
                    "test_months": 12,
                    "train_duplicate_asset_date_rows": 0,
                    "test_duplicate_asset_date_rows": 0,
                },
                {
                    "window_id": "train_2021_test_2022",
                    "train_start": "2021-01-31",
                    "train_end": "2021-12-31",
                    "test_start": "2022-01-31",
                    "test_end": "2022-12-31",
                    "train_rows": 2,
                    "test_rows": 1,
                    "train_assets": 1,
                    "test_assets": 1,
                    "train_months": 12,
                    "test_months": 12,
                    "train_duplicate_asset_date_rows": 0,
                    "test_duplicate_asset_date_rows": 0,
                },
            ],
        },
    )
    write_json_artifact(
        sklearn_dir / "summary.json",
        {
            "status": "ok",
            "stage": "crsp_sklearn_baseline",
            "splits_dir": str(walkforward_dir),
            "model_name": "ridge",
            "feature_cols": [
                "mom12_1",
                "mom6_1",
                "mom3_1",
                "ret1_0",
            ],
            "label_col": "forward_1m_total_ret",
            "quantile": 0.1,
            "random_state": 0,
            "windows": 2,
            "window_ids": ["train_2020_test_2021", "train_2021_test_2022"],
            "prediction_rows": 4,
            "date_min": "2021-01-31",
            "date_max": "2022-12-31",
            "average_mse": 0.125,
            "average_mae": 0.15,
            "average_prediction_ic": 0.15,
            "average_prediction_rank_ic": 0.125,
            "portfolio_rows": 3,
            "portfolio_date_min": "2021-01-31",
            "portfolio_date_max": "2021-03-31",
            "cumulative_return": 0.019494,
            "annualized_return": 0.079633,
            "annualized_volatility": 0.087177,
            "sharpe": 0.913678,
            "mean_monthly_return": 0.006667,
            "std_monthly_return": 0.025166,
            "positive_month_ratio": 0.666667,
            "worst_month": -0.02,
            "best_month": 0.03,
        },
    )
    write_json_artifact(
        sklearn_dir / "window_metrics.json",
        {
            "status": "ok",
            "stage": "crsp_sklearn_baseline",
            "splits_dir": str(walkforward_dir),
            "model_name": "ridge",
            "feature_cols": [
                "mom12_1",
                "mom6_1",
                "mom3_1",
                "ret1_0",
            ],
            "label_col": "forward_1m_total_ret",
            "quantile": 0.1,
            "random_state": 0,
            "window_count": 2,
            "window_metrics": [
                {
                    "window_id": "train_2020_test_2021",
                    "model_name": "ridge",
                    "feature_cols": ["mom12_1", "mom6_1", "mom3_1", "ret1_0"],
                    "label_col": "forward_1m_total_ret",
                    "train_rows": 2,
                    "train_rows_used": 2,
                    "train_missing_label_rows": 0,
                    "test_rows": 1,
                    "prediction_rows": 1,
                    "valid_prediction_rows": 1,
                    "date_min": "2021-01-31",
                    "date_max": "2021-01-31",
                    "train_date_min": "2020-01-31",
                    "train_date_max": "2020-12-31",
                    "test_date_min": "2021-01-31",
                    "test_date_max": "2021-12-31",
                    "asset_count": 1,
                    "date_count": 1,
                    "mse": 0.1,
                    "mae": 0.12,
                    "prediction_ic": 0.5,
                    "prediction_rank_ic": 0.4,
                    "prediction_ic_observation_count": 1,
                    "prediction_rank_ic_observation_count": 1,
                },
                {
                    "window_id": "train_2021_test_2022",
                    "model_name": "ridge",
                    "feature_cols": ["mom12_1", "mom6_1", "mom3_1", "ret1_0"],
                    "label_col": "forward_1m_total_ret",
                    "train_rows": 2,
                    "train_rows_used": 2,
                    "train_missing_label_rows": 0,
                    "test_rows": 1,
                    "prediction_rows": 1,
                    "valid_prediction_rows": 1,
                    "date_min": "2022-01-31",
                    "date_max": "2022-01-31",
                    "train_date_min": "2021-01-31",
                    "train_date_max": "2021-12-31",
                    "test_date_min": "2022-01-31",
                    "test_date_max": "2022-12-31",
                    "asset_count": 1,
                    "date_count": 1,
                    "mse": 0.15,
                    "mae": 0.18,
                    "prediction_ic": -0.2,
                    "prediction_rank_ic": -0.1,
                    "prediction_ic_observation_count": 1,
                    "prediction_rank_ic_observation_count": 1,
                },
            ],
        },
    )
    _make_portfolio_returns().to_parquet(sklearn_dir / "prediction_portfolio_returns.parquet", index=False)
    return e2e_dir


def test_load_crsp_ml_e2e_artifacts_missing_required_file_raises_clear_error(tmp_path: Path) -> None:
    e2e_dir = tmp_path / "crsp_ml_e2e"
    (e2e_dir / "dataset").mkdir(parents=True, exist_ok=True)

    with pytest.raises(FileNotFoundError, match="e2e_summary.json"):
        load_crsp_ml_e2e_artifacts(e2e_dir)


def test_build_crsp_ml_e2e_report_payload_contains_expected_sections_and_summaries(tmp_path: Path) -> None:
    e2e_dir = _make_e2e_artifacts(tmp_path)
    artifacts = load_crsp_ml_e2e_artifacts(e2e_dir)

    report = build_crsp_ml_e2e_report_payload(artifacts)

    assert report["title"] == "CRSP ML E2E Report"
    assert report["generated_at"]
    assert set(
        report.keys()
    ) == {
        "title",
        "generated_at",
        "pipeline_summary",
        "dataset_summary",
        "walkforward_summary",
        "model_summary",
        "window_metrics_summary",
        "portfolio_summary",
        "limitations",
        "artifact_paths",
    }

    pipeline_summary = report["pipeline_summary"]
    dataset_summary = report["dataset_summary"]
    walkforward_summary = report["walkforward_summary"]
    model_summary = report["model_summary"]
    window_summary = report["window_metrics_summary"]
    portfolio_summary = report["portfolio_summary"]

    assert pipeline_summary["monthly_input"] == "/input/crsp_monthly.parquet"
    assert pipeline_summary["output_dir"] == str(e2e_dir)
    assert pipeline_summary["dataset_rows"] == 6
    assert pipeline_summary["dataset_assets"] == 2
    assert pipeline_summary["dataset_date_min"] == "2020-01-31"
    assert pipeline_summary["dataset_date_max"] == "2020-03-31"
    assert pipeline_summary["walkforward_windows"] == 2
    assert pipeline_summary["model_name"] == "ridge"
    assert pipeline_summary["prediction_rows"] == 4
    assert pipeline_summary["prediction_date_min"] == "2021-01-31"
    assert pipeline_summary["prediction_date_max"] == "2022-12-31"

    assert dataset_summary["rows"] == 6
    assert dataset_summary["assets"] == 2
    assert dataset_summary["months"] == 3
    assert dataset_summary["date_min"] == "2020-01-31"
    assert dataset_summary["date_max"] == "2020-03-31"
    assert dataset_summary["missing_label_ratio"] == 0.1667
    assert dataset_summary["duplicate_asset_date_rows"] == 0

    assert walkforward_summary["windows"] == 2
    assert walkforward_summary["first_window_id"] == "train_2020_test_2021"
    assert walkforward_summary["last_window_id"] == "train_2021_test_2022"
    assert walkforward_summary["total_train_rows"] == 4
    assert walkforward_summary["total_test_rows"] == 2
    assert walkforward_summary["first_train_start"] == "2020-01-31"
    assert walkforward_summary["last_test_end"] == "2022-12-31"

    assert model_summary["model_name"] == "ridge"
    assert model_summary["prediction_rows"] == 4
    assert model_summary["average_mse"] == 0.125
    assert model_summary["average_mae"] == 0.15
    assert model_summary["average_prediction_ic"] == 0.15
    assert model_summary["average_prediction_rank_ic"] == 0.125

    assert window_summary["window_count"] == 2
    assert window_summary["positive_prediction_ic_windows"] == 1
    assert window_summary["positive_prediction_rank_ic_windows"] == 1
    assert window_summary["mean_prediction_ic"] == 0.15
    assert window_summary["median_prediction_ic"] == 0.15
    assert window_summary["best_prediction_ic_window"]["window_id"] == "train_2020_test_2021"
    assert window_summary["worst_prediction_ic_window"]["window_id"] == "train_2021_test_2022"
    assert window_summary["best_prediction_rank_ic_window"]["window_id"] == "train_2020_test_2021"
    assert window_summary["worst_prediction_rank_ic_window"]["window_id"] == "train_2021_test_2022"
    assert len(window_summary["window_metrics_preview"]) == 2

    assert portfolio_summary["rows"] == 3
    assert portfolio_summary["date_min"] == "2021-01-31"
    assert portfolio_summary["date_max"] == "2021-03-31"
    assert portfolio_summary["cumulative_return"] == 0.019494
    assert portfolio_summary["cumulative_return_preview"][0]["date"] == "2021-01-31"
    assert len(portfolio_summary["cumulative_return_preview"]) == 3


def test_render_crsp_ml_e2e_report_markdown_contains_expected_headings(tmp_path: Path) -> None:
    e2e_dir = _make_e2e_artifacts(tmp_path)
    report = build_crsp_ml_e2e_report_payload(load_crsp_ml_e2e_artifacts(e2e_dir))

    markdown = render_crsp_ml_e2e_report_markdown(report)

    assert "# CRSP ML E2E Report" in markdown
    assert "## Pipeline Overview" in markdown
    assert "## Dataset" in markdown
    assert "## Walk-Forward Splits" in markdown
    assert "## Sklearn Baseline" in markdown
    assert "## Prediction Portfolio" in markdown
    assert "## Window Diagnostics" in markdown
    assert "## Limitations" in markdown
    assert "## Artifact Layout" in markdown


def test_render_crsp_ml_e2e_report_html_contains_expected_sections(tmp_path: Path) -> None:
    e2e_dir = _make_e2e_artifacts(tmp_path)
    report = build_crsp_ml_e2e_report_payload(load_crsp_ml_e2e_artifacts(e2e_dir))

    html = render_crsp_ml_e2e_report_html(report)

    assert "<h1>CRSP ML E2E Report</h1>" in html
    assert "<h2>Pipeline Overview</h2>" in html
    assert "<h2>Dataset</h2>" in html
    assert "<h2>Walk-Forward Splits</h2>" in html
    assert "<h2>Sklearn Baseline</h2>" in html
    assert "<h2>Prediction Portfolio</h2>" in html
    assert "<h2>Window Diagnostics</h2>" in html
    assert "<h2>Limitations</h2>" in html
    assert "<h2>Artifact Layout</h2>" in html


def test_write_crsp_ml_e2e_report_writes_default_artifacts(tmp_path: Path) -> None:
    e2e_dir = _make_e2e_artifacts(tmp_path)
    output_dir = tmp_path / "report"

    report = write_crsp_ml_e2e_report(e2e_dir, output_dir)

    report_json_path = output_dir / "report.json"
    report_md_path = output_dir / "report.md"
    report_html_path = output_dir / "report.html"

    assert report_json_path.exists()
    assert report_md_path.exists()
    assert report_html_path.exists()
    assert json.loads(report_json_path.read_text(encoding="utf-8")) == report
    assert report["artifact_paths"]["report_dir"] == str(output_dir)
    assert report["artifact_paths"]["report_json"] == str(report_json_path)
    assert report["artifact_paths"]["report_md"] == str(report_md_path)
    assert report["artifact_paths"]["report_html"] == str(report_html_path)


def test_write_crsp_ml_e2e_report_skips_html_when_requested(tmp_path: Path) -> None:
    e2e_dir = _make_e2e_artifacts(tmp_path)
    output_dir = tmp_path / "report"

    report = write_crsp_ml_e2e_report(e2e_dir, output_dir, write_html=False)

    assert (output_dir / "report.json").exists()
    assert (output_dir / "report.md").exists()
    assert not (output_dir / "report.html").exists()
    assert report["artifact_paths"]["report_html"] is None


def test_build_crsp_ml_e2e_report_cli_smoke_writes_report_artifacts(tmp_path: Path) -> None:
    e2e_dir = _make_e2e_artifacts(tmp_path)
    output_dir = tmp_path / "report_cli"

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--e2e-dir",
            str(e2e_dir),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr

    stdout_report = json.loads(result.stdout)
    file_report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))

    assert stdout_report == file_report
    assert file_report["title"] == "CRSP ML E2E Report"
    assert (output_dir / "report.json").exists()
    assert (output_dir / "report.md").exists()
    assert (output_dir / "report.html").exists()
