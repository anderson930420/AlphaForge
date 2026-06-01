from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alphaforge.crsp_ml_result_diagnostics import (
    build_crsp_ml_result_diagnostics,
    compare_ml_vs_mom12m,
    load_crsp_ml_result_artifacts,
    render_crsp_ml_result_diagnostics_markdown,
    summarize_portfolio_returns,
    summarize_window_metrics,
    write_crsp_ml_result_diagnostics,
)
from alphaforge.json_utils import write_json_artifact


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_crsp_ml_result_diagnostics.py"


def _make_portfolio_returns(dates: list[str], returns: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"date": pd.to_datetime(dates), "long_short_ret": returns})


def _write_ml_result_artifacts(root: Path) -> tuple[Path, Path]:
    ml_dir = root / "crsp_ml_e2e"
    sklearn_dir = ml_dir / "sklearn_baseline"
    sklearn_dir.mkdir(parents=True, exist_ok=True)

    write_json_artifact(
        ml_dir / "e2e_summary.json",
        {
            "status": "ok",
            "stage": "crsp_ml_e2e_pipeline",
            "output_dir": str(ml_dir),
            "dataset_rows": 6,
            "dataset_assets": 2,
            "dataset_date_min": "2020-01-31",
            "dataset_date_max": "2020-03-31",
            "walkforward_windows": 3,
            "prediction_rows": 6,
            "prediction_date_min": "2021-01-31",
            "prediction_date_max": "2021-03-31",
            "portfolio_rows": 3,
            "portfolio_cumulative_return": 0.0659,
            "portfolio_annualized_return": 0.2731,
            "portfolio_sharpe": 1.8912,
        },
    )
    write_json_artifact(
        sklearn_dir / "summary.json",
        {
            "status": "ok",
            "stage": "crsp_sklearn_baseline",
            "splits_dir": str(ml_dir / "walkforward"),
            "model_name": "ridge",
            "label_col": "forward_1m_total_ret",
            "quantile": 0.1,
            "random_state": 0,
            "windows": 3,
            "prediction_rows": 6,
            "average_mse": 0.18,
            "average_mae": 0.12,
            "average_prediction_ic": 0.04,
            "average_prediction_rank_ic": -0.03,
            "portfolio_rows": 3,
            "cumulative_return": 0.0659,
            "annualized_return": 0.2731,
            "annualized_volatility": 0.1445,
            "sharpe": 1.8912,
            "mean_monthly_return": 0.0214,
            "std_monthly_return": 0.0417,
            "positive_month_ratio": 0.6667,
            "best_month": 0.10,
            "worst_month": -0.05,
            "max_drawdown": -0.05,
        },
    )
    write_json_artifact(
        sklearn_dir / "window_metrics.json",
        {
            "status": "ok",
            "stage": "crsp_sklearn_baseline",
            "window_count": 3,
            "window_metrics": [
                {
                    "window_id": "w1",
                    "mse": 0.10,
                    "mae": 0.05,
                    "prediction_ic": 0.10,
                    "prediction_rank_ic": 0.20,
                },
                {
                    "window_id": "w2",
                    "mse": 0.20,
                    "mae": 0.10,
                    "prediction_ic": -0.02,
                    "prediction_rank_ic": -0.10,
                },
                {
                    "window_id": "w3",
                    "mse": 0.30,
                    "mae": 0.15,
                    "prediction_ic": np.nan,
                    "prediction_rank_ic": 0.05,
                },
            ],
        },
    )
    _make_portfolio_returns(
        ["2021-01-31", "2021-02-28", "2021-03-31"],
        [0.10, -0.05, 0.02],
    ).to_parquet(sklearn_dir / "prediction_portfolio_returns.parquet", index=False)

    mom_dir = root / "crsp_mom12m_baseline"
    mom_dir.mkdir(parents=True, exist_ok=True)
    write_json_artifact(
        mom_dir / "momentum_summary.json",
        {
            "status": "ok",
            "stage": "crsp_mom12m_baseline",
            "input": "/synthetic/input.parquet",
            "output_dir": str(mom_dir),
            "quantile": 0.1,
            "min_obs": 8,
            "weighting": "equal",
            "signal_panel_rows": 6,
            "portfolio_rows": 3,
            "cumulative_return": 0.1550,
            "annualized_return": 0.6650,
            "annualized_volatility": 0.1660,
            "sharpe": 4.0060,
            "mean_monthly_return": 0.0500,
            "std_monthly_return": 0.0400,
            "positive_month_ratio": 0.6667,
            "best_month": 0.10,
            "worst_month": -0.05,
            "max_drawdown": -0.05,
        },
    )
    _make_portfolio_returns(
        ["2021-02-28", "2021-03-31", "2021-04-30"],
        [0.05, 0.10, 0.01],
    ).to_parquet(mom_dir / "momentum_portfolio_returns.parquet", index=False)

    return ml_dir, mom_dir


def test_load_crsp_ml_result_artifacts_missing_required_file_raises_clear_error(tmp_path: Path) -> None:
    ml_dir = tmp_path / "crsp_ml_e2e"
    (ml_dir / "sklearn_baseline").mkdir(parents=True, exist_ok=True)

    with pytest.raises(FileNotFoundError, match="e2e_summary.json"):
        load_crsp_ml_result_artifacts(ml_e2e_dir=ml_dir)


def test_summarize_window_metrics_computes_positive_ic_ratio_and_extrema() -> None:
    summary = summarize_window_metrics(
        [
            {"window_id": "w1", "mse": 0.10, "mae": 0.05, "prediction_ic": 0.10, "prediction_rank_ic": 0.20},
            {"window_id": "w2", "mse": 0.20, "mae": 0.10, "prediction_ic": -0.02, "prediction_rank_ic": -0.10},
            {"window_id": "w3", "mse": 0.30, "mae": 0.15, "prediction_ic": np.nan, "prediction_rank_ic": 0.05},
        ]
    )

    assert summary["windows"] == 3
    assert summary["mean_prediction_ic"] == pytest.approx(0.04)
    assert summary["median_prediction_ic"] == pytest.approx(0.04)
    assert summary["positive_ic_windows"] == 1
    assert summary["positive_ic_ratio"] == pytest.approx(0.5)
    assert summary["positive_rank_ic_windows"] == 2
    assert summary["positive_rank_ic_ratio"] == pytest.approx(2 / 3)
    assert summary["best_ic_window"]["window_id"] == "w1"
    assert summary["worst_ic_window"]["window_id"] == "w2"
    assert summary["best_rank_ic_window"]["window_id"] == "w1"
    assert summary["worst_rank_ic_window"]["window_id"] == "w2"


def test_summarize_portfolio_returns_computes_cumulative_return_and_max_drawdown() -> None:
    portfolio_returns = _make_portfolio_returns(
        ["2021-01-31", "2021-02-28", "2021-03-31"],
        [0.10, -0.05, 0.02],
    )

    summary = summarize_portfolio_returns(portfolio_returns)

    assert summary["rows"] == 3
    assert summary["date_min"] == "2021-01-31"
    assert summary["date_max"] == "2021-03-31"
    assert summary["cumulative_return"] == pytest.approx(0.0659, rel=1e-4)
    assert summary["mean_monthly_return"] == pytest.approx(0.0233333333)
    assert summary["best_month"] == pytest.approx(0.10)
    assert summary["worst_month"] == pytest.approx(-0.05)
    assert summary["max_drawdown"] == pytest.approx(-0.05)


def test_compare_ml_vs_mom12m_aligns_overlapping_dates_only() -> None:
    ml_returns = _make_portfolio_returns(
        ["2021-01-31", "2021-02-28", "2021-03-31"],
        [0.10, 0.00, 0.20],
    )
    mom_returns = _make_portfolio_returns(
        ["2021-02-28", "2021-03-31", "2021-04-30"],
        [0.05, 0.10, 0.01],
    )

    comparison = compare_ml_vs_mom12m(ml_returns, mom_returns)

    assert comparison["overlap_rows"] == 2
    assert comparison["overlap_date_min"] == "2021-02-28"
    assert comparison["overlap_date_max"] == "2021-03-31"
    assert comparison["ml_summary"]["rows"] == 2
    assert comparison["mom12m_summary"]["rows"] == 2
    assert comparison["ml_cumulative_return"] == pytest.approx(0.20)
    assert comparison["mom12m_cumulative_return"] == pytest.approx(0.155)
    assert comparison["spread_cumulative_return"] == pytest.approx(0.045)
    assert comparison["ml_outperformed_months"] == 1
    assert comparison["ml_outperformed_month_ratio"] == pytest.approx(0.5)


def test_compare_ml_vs_mom12m_raises_when_no_overlap() -> None:
    ml_returns = _make_portfolio_returns(["2021-01-31"], [0.10])
    mom_returns = _make_portfolio_returns(["2021-02-28"], [0.05])

    with pytest.raises(ValueError, match="No overlapping dates"):
        compare_ml_vs_mom12m(ml_returns, mom_returns)


def test_build_crsp_ml_result_diagnostics_contains_expected_top_level_sections(tmp_path: Path) -> None:
    ml_dir, mom_dir = _write_ml_result_artifacts(tmp_path)
    artifacts = load_crsp_ml_result_artifacts(ml_e2e_dir=ml_dir, mom12m_dir=mom_dir)

    diagnostics = build_crsp_ml_result_diagnostics(artifacts)

    assert diagnostics["title"] == "CRSP ML Result Diagnostics"
    assert diagnostics["generated_at"]
    assert diagnostics["ml_e2e_summary"]["dataset_rows"] == 6
    assert diagnostics["ml_sklearn_summary"]["model_name"] == "ridge"
    assert diagnostics["window_diagnostics"]["windows"] == 3
    assert diagnostics["ml_portfolio_summary"]["rows"] == 3
    assert diagnostics["mom12m_summary"]["portfolio_rows"] == 3
    assert diagnostics["comparison"]["overlap_rows"] == 2
    assert isinstance(diagnostics["interpretation"], list)
    assert diagnostics["interpretation"]
    assert "No transaction costs" in diagnostics["limitations"]
    assert diagnostics["artifact_paths"]["ml_e2e_dir"] == str(ml_dir)
    assert diagnostics["artifact_paths"]["mom12m_dir"] == str(mom_dir)


def test_render_crsp_ml_result_diagnostics_markdown_contains_expected_headings(tmp_path: Path) -> None:
    ml_dir, mom_dir = _write_ml_result_artifacts(tmp_path)
    diagnostics = build_crsp_ml_result_diagnostics(load_crsp_ml_result_artifacts(ml_e2e_dir=ml_dir, mom12m_dir=mom_dir))

    markdown = render_crsp_ml_result_diagnostics_markdown(diagnostics)

    assert "# CRSP ML Result Diagnostics" in markdown
    assert "## Executive Summary" in markdown
    assert "## ML Baseline Summary" in markdown
    assert "## Walk-Forward Window Diagnostics" in markdown
    assert "## Prediction Portfolio" in markdown
    assert "## ML vs Mom12m Benchmark Comparison" in markdown
    assert "## Interpretation" in markdown
    assert "## Limitations" in markdown
    assert "## Artifact Inputs / Outputs" in markdown


def test_write_crsp_ml_result_diagnostics_writes_artifacts(tmp_path: Path) -> None:
    ml_dir, mom_dir = _write_ml_result_artifacts(tmp_path)
    output_dir = tmp_path / "diagnostics"

    diagnostics = write_crsp_ml_result_diagnostics(
        ml_e2e_dir=ml_dir,
        output_dir=output_dir,
        mom12m_dir=mom_dir,
    )

    json_path = output_dir / "diagnostics.json"
    md_path = output_dir / "diagnostics.md"

    assert json_path.exists()
    assert md_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8")) == diagnostics
    assert diagnostics["artifact_paths"]["output_dir"] == str(output_dir)
    assert diagnostics["artifact_paths"]["diagnostics_json"] == str(json_path)
    assert diagnostics["artifact_paths"]["diagnostics_md"] == str(md_path)


def test_build_crsp_ml_result_diagnostics_cli_smoke_writes_report_artifacts(tmp_path: Path) -> None:
    ml_dir, mom_dir = _write_ml_result_artifacts(tmp_path)
    output_dir = tmp_path / "diagnostics_cli"

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--ml-e2e-dir",
            str(ml_dir),
            "--mom12m-dir",
            str(mom_dir),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr

    stdout_payload = json.loads(result.stdout)
    file_payload = json.loads((output_dir / "diagnostics.json").read_text(encoding="utf-8"))

    assert stdout_payload == file_payload
    assert file_payload["title"] == "CRSP ML Result Diagnostics"
    assert (output_dir / "diagnostics.json").exists()
    assert (output_dir / "diagnostics.md").exists()
