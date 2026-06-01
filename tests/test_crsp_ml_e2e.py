from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge import crsp_ml_e2e
from alphaforge.crsp_ml_dataset import CRSP_ML_LABEL_COLUMN
from alphaforge.crsp_ml_e2e import run_crsp_ml_e2e_pipeline


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_crsp_ml_e2e_pipeline.py"


def _make_asset_rows(
    asset_id: str,
    permno: int,
    ticker: str,
    returns: list[float],
    *,
    common: bool,
    primary: bool,
    price_start: float = 20.0,
    market_cap_start: float = 2000.0,
    lag_market_cap_start: float = 1900.0,
    volume_start: float = 1000.0,
    shares_out_start: float = 100.0,
) -> list[dict[str, object]]:
    dates = pd.date_range("2000-01-31", periods=len(returns), freq="ME")
    rows: list[dict[str, object]] = []
    for index, (date_value, total_ret) in enumerate(zip(dates, returns)):
        base = index * 10.0
        price = price_start + base
        volume = volume_start + (index * 100.0)
        shares_out = shares_out_start + (index * 10.0)
        market_cap = market_cap_start + (index * 120.0)
        lag_market_cap = lag_market_cap_start + (index * 110.0)
        rows.append(
            {
                "date": date_value,
                "asset_id": asset_id,
                "permno": permno,
                "permco": permno + 1000,
                "ticker": ticker,
                "cusip": f"{permno:08d}",
                "ncusip": f"{permno:08d}",
                "exchcd": 1 if primary else 3,
                "shrcd": 10 if common else 11,
                "siccd": 1234,
                "price": price,
                "ret": total_ret,
                "retx": total_ret,
                "dlret": 0.0,
                "volume": volume,
                "shares_out": shares_out,
                "market_cap": market_cap,
                "lag_market_cap": lag_market_cap,
                "total_ret": total_ret,
                "is_common_share": common,
                "is_primary_us_exchange": primary,
                "daily_obs_count": 20,
                "first_trading_date": "1990-01-31",
                "last_trading_date": date_value,
            }
        )
    return rows


def _make_panel() -> pd.DataFrame:
    a_returns = [0.01] * 168
    b_returns = [0.02] * 168
    c_returns = [0.03] * 168
    d_returns = [0.04] * 168
    e_returns = [0.05] * 168

    rows: list[dict[str, object]] = []
    rows.extend(_make_asset_rows("A", 10001, "AAA", a_returns, common=True, primary=True))
    rows.extend(_make_asset_rows("B", 10002, "BBB", b_returns, common=True, primary=True))
    rows.extend(_make_asset_rows("C", 10003, "CCC", c_returns, common=True, primary=True))
    rows.extend(_make_asset_rows("D", 10004, "DDD", d_returns, common=False, primary=True))
    rows.extend(_make_asset_rows("E", 10005, "EEE", e_returns, common=True, primary=False))
    frame = pd.DataFrame(rows)
    return frame.sample(frac=1.0, random_state=7).reset_index(drop=True)


def test_run_crsp_ml_e2e_pipeline_raises_clear_sklearn_error_when_dependency_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _raise_import_error() -> None:
        raise ImportError(
            "scikit-learn is required for the CRSP sklearn baseline.\n"
            'Install with: python3 -m pip install -e ".[sklearn]"'
        )

    monkeypatch.setattr(crsp_ml_e2e, "require_sklearn", _raise_import_error)

    with pytest.raises(ImportError, match="scikit-learn is required for the CRSP sklearn baseline"):
        run_crsp_ml_e2e_pipeline(
            monthly_input=tmp_path / "missing.parquet",
            output_dir=tmp_path / "out",
        )


def test_run_crsp_ml_e2e_pipeline_writes_all_artifacts(tmp_path: Path) -> None:
    pytest.importorskip("sklearn")

    input_path = tmp_path / "crsp_monthly.parquet"
    output_dir = tmp_path / "crsp_ml_e2e"
    _make_panel().to_parquet(input_path, index=False)

    summary = run_crsp_ml_e2e_pipeline(
        monthly_input=input_path,
        output_dir=output_dir,
        start_date="2000-01-31",
        end_date="2013-12-31",
        min_mom_obs=8,
        drop_missing_label=True,
        drop_missing_features=False,
        common_shares_only=True,
        primary_exchange_only=True,
        train_years=10,
        test_years=1,
        step_years=1,
        model_name="ridge",
        quantile=0.25,
        random_state=7,
    )

    dataset_dir = output_dir / "dataset"
    walkforward_dir = output_dir / "walkforward"
    baseline_dir = output_dir / "sklearn_baseline"

    dataset_path = dataset_dir / "crsp_ml_dataset.parquet"
    dataset_qc_path = dataset_dir / "crsp_ml_dataset_qc.json"
    walkforward_qc_path = walkforward_dir / "walk_forward_qc.json"
    walkforward_manifest_path = walkforward_dir / "walk_forward_manifest.json"
    predictions_path = baseline_dir / "predictions.parquet"
    window_metrics_path = baseline_dir / "window_metrics.json"
    portfolio_path = baseline_dir / "prediction_portfolio_returns.parquet"
    baseline_summary_path = baseline_dir / "summary.json"
    e2e_summary_path = output_dir / "e2e_summary.json"

    for path in [
        dataset_path,
        dataset_qc_path,
        walkforward_qc_path,
        walkforward_manifest_path,
        predictions_path,
        window_metrics_path,
        portfolio_path,
        baseline_summary_path,
        e2e_summary_path,
    ]:
        assert path.exists()

    file_summary = json.loads(e2e_summary_path.read_text(encoding="utf-8"))
    dataset_qc = json.loads(dataset_qc_path.read_text(encoding="utf-8"))
    walkforward_qc = json.loads(walkforward_qc_path.read_text(encoding="utf-8"))
    manifest = json.loads(walkforward_manifest_path.read_text(encoding="utf-8"))
    window_metrics = json.loads(window_metrics_path.read_text(encoding="utf-8"))
    baseline_summary = json.loads(baseline_summary_path.read_text(encoding="utf-8"))
    predictions = pd.read_parquet(predictions_path)
    portfolio = pd.read_parquet(portfolio_path)
    dataset = pd.read_parquet(dataset_path)

    assert summary == file_summary
    assert file_summary["status"] == "ok"
    assert file_summary["stage"] == "crsp_ml_e2e_pipeline"
    assert file_summary["monthly_input"] == str(input_path)
    assert file_summary["output_dir"] == str(output_dir)
    assert file_summary["start_date"] == "2000-01-31"
    assert file_summary["end_date"] == "2013-12-31"
    assert file_summary["min_mom_obs"] == 8
    assert file_summary["drop_missing_label"] is True
    assert file_summary["drop_missing_features"] is False
    assert file_summary["common_shares_only"] is True
    assert file_summary["primary_exchange_only"] is True
    assert file_summary["train_years"] == 10
    assert file_summary["test_years"] == 1
    assert file_summary["step_years"] == 1
    assert file_summary["model_name"] == "ridge"
    assert file_summary["quantile"] == pytest.approx(0.25)
    assert file_summary["random_state"] == 7
    assert file_summary["dataset_rows"] == 501
    assert file_summary["dataset_assets"] == 3
    assert file_summary["dataset_date_min"] == "2000-01-31"
    assert file_summary["dataset_date_max"] == "2013-11-30"
    assert file_summary["walkforward_windows"] == 3
    assert file_summary["first_window_id"] == "train_2000-2009_test_2010"
    assert file_summary["last_window_id"] == "train_2002-2011_test_2012"
    assert file_summary["total_train_rows"] == 1080
    assert file_summary["total_test_rows"] == 108
    assert file_summary["prediction_rows"] == 108
    assert file_summary["prediction_date_min"] == "2010-01-31"
    assert file_summary["prediction_date_max"] == "2012-12-31"
    assert file_summary["average_mse"] is not None
    assert file_summary["average_mae"] is not None
    assert file_summary["average_prediction_ic"] is not None
    assert file_summary["average_prediction_rank_ic"] is not None
    assert file_summary["portfolio_rows"] == 36
    assert file_summary["portfolio_cumulative_return"] is not None
    assert file_summary["portfolio_annualized_return"] is not None
    assert file_summary["portfolio_sharpe"] is not None
    assert file_summary["created_at"]

    assert dataset["asset_id"].nunique() == 3
    assert set(dataset["asset_id"].unique()) == {"A", "B", "C"}
    assert dataset["date"].min() == pd.Timestamp("2000-01-31")
    assert dataset["date"].max() == pd.Timestamp("2013-11-30")
    assert list(dataset.columns)[-1] == CRSP_ML_LABEL_COLUMN

    assert dataset_qc["status"] == "ok"
    assert dataset_qc["rows"] == 501
    assert dataset_qc["assets"] == 3
    assert walkforward_qc["status"] == "ok"
    assert walkforward_qc["windows"] == 3
    assert walkforward_qc["total_train_rows"] == 1080
    assert walkforward_qc["total_test_rows"] == 108
    assert manifest["status"] == "ok"
    assert manifest["window_count"] == 3
    assert [window["window_id"] for window in manifest["windows"]] == [
        "train_2000-2009_test_2010",
        "train_2001-2010_test_2011",
        "train_2002-2011_test_2012",
    ]
    assert window_metrics["status"] == "ok"
    assert window_metrics["window_count"] == 3
    assert len(window_metrics["window_metrics"]) == 3
    assert baseline_summary["status"] == "ok"
    assert baseline_summary["windows"] == 3
    assert baseline_summary["prediction_rows"] == len(predictions)
    assert baseline_summary["portfolio_rows"] == len(portfolio)
    assert predictions["window_id"].nunique() == 3
    assert {"window_id", "model_name", "predicted_return", "forward_1m_total_ret"}.issubset(
        set(predictions.columns)
    )
    assert {"date", "long_short_ret", "quantile"}.issubset(set(portfolio.columns))


def test_run_crsp_ml_e2e_pipeline_cli_writes_summary_and_artifacts(tmp_path: Path) -> None:
    pytest.importorskip("sklearn")

    input_path = tmp_path / "crsp_monthly.parquet"
    output_dir = tmp_path / "crsp_ml_e2e"
    _make_panel().to_parquet(input_path, index=False)

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--monthly-input",
            str(input_path),
            "--output-dir",
            str(output_dir),
            "--start-date",
            "2000-01-31",
            "--end-date",
            "2013-12-31",
            "--min-mom-obs",
            "8",
            "--drop-missing-label",
            "--common-shares-only",
            "--primary-exchange-only",
            "--train-years",
            "10",
            "--test-years",
            "1",
            "--step-years",
            "1",
            "--model",
            "ridge",
            "--quantile",
            "0.25",
            "--random-state",
            "7",
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr

    summary_path = output_dir / "e2e_summary.json"
    baseline_summary_path = output_dir / "sklearn_baseline" / "summary.json"
    predictions_path = output_dir / "sklearn_baseline" / "predictions.parquet"
    portfolio_path = output_dir / "sklearn_baseline" / "prediction_portfolio_returns.parquet"

    stdout_summary = json.loads(result.stdout)
    file_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    baseline_summary = json.loads(baseline_summary_path.read_text(encoding="utf-8"))

    assert stdout_summary == file_summary
    assert file_summary["status"] == "ok"
    assert file_summary["model_name"] == "ridge"
    assert file_summary["dataset_rows"] == 501
    assert file_summary["walkforward_windows"] == 3
    assert baseline_summary["status"] == "ok"
    assert baseline_summary["windows"] == 3
    assert predictions_path.exists()
    assert portfolio_path.exists()
