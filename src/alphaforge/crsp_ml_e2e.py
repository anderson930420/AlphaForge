"""CRSP ML end-to-end orchestration helpers.

This module composes the existing CRSP monthly panel loader, ML dataset
builder, walk-forward splitter, and sklearn baseline into one reproducible
pipeline. It does not add new modeling logic or change the existing CRSP
feature, split, or baseline behavior.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .crsp_ml_dataset import build_crsp_ml_dataset, build_crsp_ml_dataset_qc
from .crsp_ml_walkforward import build_walk_forward_qc, build_walk_forward_splits
from .crsp_monthly_panel import load_crsp_monthly_panel
from .crsp_sklearn_baseline import require_sklearn, run_walk_forward_sklearn_baseline
from .json_utils import write_json_artifact
from .parquet_io import write_parquet_artifact


_LOADER_COLUMNS = [
    "date",
    "asset_id",
    "permno",
    "ticker",
    "total_ret",
    "ret",
    "retx",
    "dlret",
    "price",
    "volume",
    "shares_out",
    "market_cap",
    "lag_market_cap",
]


def run_crsp_ml_e2e_pipeline(
    *,
    monthly_input: str | Path,
    output_dir: str | Path,
    start_date: str | None = None,
    end_date: str | None = None,
    min_mom_obs: int = 8,
    drop_missing_label: bool = True,
    drop_missing_features: bool = False,
    common_shares_only: bool = False,
    primary_exchange_only: bool = False,
    train_years: int = 10,
    test_years: int = 1,
    step_years: int = 1,
    model_name: str = "ridge",
    quantile: float = 0.1,
    random_state: int = 0,
) -> dict[str, object]:
    """Run the CRSP ML dataset, walk-forward, and sklearn baseline pipeline."""
    require_sklearn()

    monthly_input_path = Path(monthly_input)
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    normalized_start_date = _parse_optional_month_end(start_date, field_name="start_date")
    normalized_end_date = _parse_optional_month_end(end_date, field_name="end_date")
    if normalized_start_date is not None and normalized_end_date is not None:
        if normalized_start_date > normalized_end_date:
            raise ValueError("start_date must be on or before end_date")

    dataset_dir = output_dir_path / "dataset"
    walkforward_dir = output_dir_path / "walkforward"
    sklearn_dir = output_dir_path / "sklearn_baseline"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    walkforward_dir.mkdir(parents=True, exist_ok=True)
    sklearn_dir.mkdir(parents=True, exist_ok=True)

    loader_kwargs: dict[str, object] = {
        "common_shares_only": common_shares_only,
        "primary_exchange_only": primary_exchange_only,
        "columns": _LOADER_COLUMNS,
    }
    if normalized_start_date is not None:
        loader_kwargs["start_date"] = _month_end_string(normalized_start_date)
    if normalized_end_date is not None:
        loader_kwargs["end_date"] = _month_end_string(normalized_end_date)

    panel = load_crsp_monthly_panel(monthly_input_path, **loader_kwargs)
    dataset = build_crsp_ml_dataset(
        panel,
        min_mom_obs=min_mom_obs,
        drop_missing_label=drop_missing_label,
        drop_missing_features=drop_missing_features,
    )

    dataset_path = dataset_dir / "crsp_ml_dataset.parquet"
    dataset_qc_path = dataset_dir / "crsp_ml_dataset_qc.json"
    write_parquet_artifact(dataset, dataset_path, index=False)

    dataset_qc = build_crsp_ml_dataset_qc(dataset)
    dataset_qc.update(
        {
            "status": "ok",
            "input": str(monthly_input_path),
            "output": str(dataset_path),
            "qc_output": str(dataset_qc_path),
            "start_date": _month_end_string(normalized_start_date),
            "end_date": _month_end_string(normalized_end_date),
            "min_mom_obs": int(min_mom_obs),
            "drop_missing_label": bool(drop_missing_label),
            "drop_missing_features": bool(drop_missing_features),
            "common_shares_only": bool(common_shares_only),
            "primary_exchange_only": bool(primary_exchange_only),
        }
    )
    write_json_artifact(dataset_qc_path, dataset_qc)

    splits = build_walk_forward_splits(
        dataset,
        train_years=train_years,
        test_years=test_years,
        step_years=step_years,
    )

    walk_forward_qc = build_walk_forward_qc(splits)
    walk_forward_qc_path = walkforward_dir / "walk_forward_qc.json"
    walk_forward_manifest_path = walkforward_dir / "walk_forward_manifest.json"

    manifest_windows: list[dict[str, object]] = []
    for window, train_df, test_df in splits:
        window_dir = walkforward_dir / window.window_id
        window_dir.mkdir(parents=True, exist_ok=True)
        train_path = window_dir / "train.parquet"
        test_path = window_dir / "test.parquet"
        write_parquet_artifact(train_df, train_path, index=False)
        write_parquet_artifact(test_df, test_path, index=False)
        manifest_windows.append(
            {
                "window_id": window.window_id,
                "window_dir": str(window_dir),
                "train_parquet": str(train_path),
                "test_parquet": str(test_path),
                "train_rows": int(len(train_df)),
                "test_rows": int(len(test_df)),
            }
        )

    walk_forward_qc.update(
        {
            "status": "ok",
            "input": str(dataset_path),
            "output_dir": str(walkforward_dir),
            "start_date": _month_end_string(normalized_start_date),
            "end_date": _month_end_string(normalized_end_date),
            "train_years_arg": int(train_years),
            "test_years_arg": int(test_years),
            "step_years_arg": int(step_years),
        }
    )
    write_json_artifact(walk_forward_qc_path, walk_forward_qc)

    walk_forward_manifest = {
        "status": "ok",
        "input": str(dataset_path),
        "output_dir": str(walkforward_dir),
        "start_date": _month_end_string(normalized_start_date),
        "end_date": _month_end_string(normalized_end_date),
        "train_years": int(train_years),
        "test_years": int(test_years),
        "step_years": int(step_years),
        "window_count": int(len(splits)),
        "windows": manifest_windows,
    }
    write_json_artifact(walk_forward_manifest_path, walk_forward_manifest)

    baseline_result = run_walk_forward_sklearn_baseline(
        walkforward_dir,
        model_name=model_name,
        quantile=quantile,
        random_state=random_state,
    )

    predictions_path = sklearn_dir / "predictions.parquet"
    window_metrics_path = sklearn_dir / "window_metrics.json"
    portfolio_path = sklearn_dir / "prediction_portfolio_returns.parquet"
    baseline_summary_path = sklearn_dir / "summary.json"

    write_parquet_artifact(baseline_result["predictions"], predictions_path, index=False)
    write_parquet_artifact(baseline_result["portfolio_returns"], portfolio_path, index=False)

    window_metrics_payload = {
        "status": "ok",
        "stage": "crsp_sklearn_baseline",
        "splits_dir": str(walkforward_dir),
        "model_name": model_name,
        "feature_cols": baseline_result["summary"]["feature_cols"],
        "label_col": "forward_1m_total_ret",
        "quantile": float(quantile),
        "random_state": int(random_state),
        "window_count": int(len(baseline_result["window_metrics"])),
        "window_metrics": baseline_result["window_metrics"],
    }
    write_json_artifact(window_metrics_path, window_metrics_payload)

    baseline_summary = {
        **baseline_result["summary"],
        "output_dir": str(sklearn_dir),
        "paths": {
            "predictions": str(predictions_path),
            "window_metrics": str(window_metrics_path),
            "prediction_portfolio_returns": str(portfolio_path),
            "summary": str(baseline_summary_path),
        },
    }
    write_json_artifact(baseline_summary_path, baseline_summary)

    window_ids = [entry["window_id"] for entry in manifest_windows]
    e2e_summary_path = output_dir_path / "e2e_summary.json"
    e2e_summary = {
        "status": "ok",
        "stage": "crsp_ml_e2e_pipeline",
        "monthly_input": str(monthly_input_path),
        "output_dir": str(output_dir_path),
        "start_date": _month_end_string(normalized_start_date),
        "end_date": _month_end_string(normalized_end_date),
        "min_mom_obs": int(min_mom_obs),
        "drop_missing_label": bool(drop_missing_label),
        "drop_missing_features": bool(drop_missing_features),
        "common_shares_only": bool(common_shares_only),
        "primary_exchange_only": bool(primary_exchange_only),
        "train_years": int(train_years),
        "test_years": int(test_years),
        "step_years": int(step_years),
        "model_name": model_name,
        "quantile": float(quantile),
        "random_state": int(random_state),
        "dataset_rows": int(dataset_qc["rows"]),
        "dataset_assets": int(dataset_qc["assets"]),
        "dataset_date_min": dataset_qc["date_min"],
        "dataset_date_max": dataset_qc["date_max"],
        "walkforward_windows": int(walk_forward_qc["windows"]),
        "first_window_id": window_ids[0] if window_ids else None,
        "last_window_id": window_ids[-1] if window_ids else None,
        "total_train_rows": int(walk_forward_qc["total_train_rows"]),
        "total_test_rows": int(walk_forward_qc["total_test_rows"]),
        "prediction_rows": int(baseline_summary["prediction_rows"]),
        "prediction_date_min": baseline_summary["date_min"],
        "prediction_date_max": baseline_summary["date_max"],
        "average_mse": baseline_summary["average_mse"],
        "average_mae": baseline_summary["average_mae"],
        "average_prediction_ic": baseline_summary["average_prediction_ic"],
        "average_prediction_rank_ic": baseline_summary["average_prediction_rank_ic"],
        "portfolio_rows": int(baseline_summary["portfolio_rows"]),
        "portfolio_cumulative_return": baseline_summary["cumulative_return"],
        "portfolio_annualized_return": baseline_summary["annualized_return"],
        "portfolio_sharpe": baseline_summary["sharpe"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "paths": {
            "dataset_dir": str(dataset_dir),
            "dataset_parquet": str(dataset_path),
            "dataset_qc": str(dataset_qc_path),
            "walkforward_dir": str(walkforward_dir),
            "walkforward_qc": str(walk_forward_qc_path),
            "walkforward_manifest": str(walk_forward_manifest_path),
            "sklearn_baseline_dir": str(sklearn_dir),
            "sklearn_predictions": str(predictions_path),
            "sklearn_window_metrics": str(window_metrics_path),
            "sklearn_prediction_portfolio_returns": str(portfolio_path),
            "sklearn_summary": str(baseline_summary_path),
            "e2e_summary": str(e2e_summary_path),
        },
    }
    write_json_artifact(e2e_summary_path, e2e_summary)
    return e2e_summary


def _parse_optional_month_end(value: str | None, *, field_name: str) -> pd.Timestamp | None:
    if value is None:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"{field_name} must be parseable as datetime: {value!r}")
    return (pd.Timestamp(parsed) + pd.offsets.MonthEnd(0)).normalize()


def _month_end_string(value: pd.Timestamp | None) -> str | None:
    if value is None:
        return None
    return pd.Timestamp(value).date().isoformat()
