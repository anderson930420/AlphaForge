from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.crsp_sklearn_baseline import (
    DEFAULT_CRSP_SKLEARN_FEATURE_COLUMNS,
    build_prediction_portfolio_returns,
    make_sklearn_model,
    run_walk_forward_sklearn_baseline,
    summarize_prediction_portfolio,
    train_predict_window,
    validate_training_frame,
)
from alphaforge.crsp_ml_preprocessing import write_feature_columns_json
from scripts.run_crsp_sklearn_baseline import parse_feature_cols as parse_cli_feature_cols


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_crsp_sklearn_baseline.py"
ASSETS = [
    ("A", 10001, "AAA"),
    ("B", 10002, "BBB"),
    ("C", 10003, "CCC"),
    ("D", 10004, "DDD"),
]


def _require_sklearn() -> None:
    pytest.importorskip("sklearn")


def _make_window_frame(
    start: str,
    periods: int,
    *,
    window_offset: int,
    assets: list[tuple[str, int, str]] = ASSETS,
) -> pd.DataFrame:
    dates = pd.date_range(start, periods=periods, freq="ME")
    rows: list[dict[str, object]] = []
    for month_index, date_value in enumerate(dates):
        for asset_index, (asset_id, permno, ticker) in enumerate(assets):
            base = window_offset * 100 + month_index * 10 + asset_index
            rows.append(
                {
                    "date": date_value,
                    "asset_id": asset_id,
                    "permno": permno,
                    "ticker": ticker,
                    "mom12_1": 0.20 + (base * 0.001),
                    "mom6_1": 0.15 + (base * 0.001),
                    "mom3_1": 0.10 + (base * 0.001),
                    "ret1_0": 0.05 + (base * 0.0005),
                    "volatility_12m": 0.30 + (asset_index * 0.01),
                    "turnover": 0.40 + (month_index * 0.01),
                    "log_market_cap": 7.0 + (asset_index * 0.02) + (month_index * 0.001),
                    "log_price": 2.0 + (asset_index * 0.01) + (month_index * 0.002),
                    "forward_1m_total_ret": 0.01 + (asset_index * 0.005) + (month_index * 0.001) + (window_offset * 0.01),
                }
            )
    return pd.DataFrame(rows)


def _write_splits_dir(root: Path) -> Path:
    splits_dir = root / "crsp_ml_walkforward"
    windows = [
        (
            "train_2000-2000_test_2001",
            _make_window_frame("2000-01-31", 12, window_offset=0),
            _make_window_frame("2001-01-31", 6, window_offset=1),
        ),
        (
            "train_2001-2001_test_2002",
            _make_window_frame("2000-07-31", 12, window_offset=2),
            _make_window_frame("2002-01-31", 6, window_offset=3),
        ),
    ]

    for window_id, train_df, test_df in windows:
        window_dir = splits_dir / window_id
        window_dir.mkdir(parents=True, exist_ok=True)
        train_df.to_parquet(window_dir / "train.parquet", index=False)
        test_df.to_parquet(window_dir / "test.parquet", index=False)

    return splits_dir


def test_cli_feature_cols_parser_filters_empty_items() -> None:
    assert parse_cli_feature_cols("mom12_1, mom6_1,") == ["mom12_1", "mom6_1"]


def test_cli_feature_cols_parser_allows_omitted_value() -> None:
    assert parse_cli_feature_cols(None) is None


def test_cli_feature_cols_parser_rejects_empty_parsed_list() -> None:
    with pytest.raises(ValueError, match="no valid feature columns"):
        parse_cli_feature_cols(" , , ")


def test_make_sklearn_model_rejects_unknown_model_name() -> None:
    with pytest.raises(ValueError, match="Unsupported model name: unknown"):
        make_sklearn_model("unknown")


def test_validate_training_frame_rejects_missing_feature_columns() -> None:
    frame = _make_window_frame("2000-01-31", 3, window_offset=0).drop(columns=["mom3_1"])

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_training_frame(
            frame,
            feature_cols=list(DEFAULT_CRSP_SKLEARN_FEATURE_COLUMNS),
            label_col="forward_1m_total_ret",
        )


def test_validate_training_frame_rejects_duplicate_asset_date_rows() -> None:
    frame = _make_window_frame("2000-01-31", 3, window_offset=0)
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate asset_id/date rows are not allowed"):
        validate_training_frame(
            frame,
            feature_cols=list(DEFAULT_CRSP_SKLEARN_FEATURE_COLUMNS),
            label_col="forward_1m_total_ret",
        )


@pytest.mark.parametrize("model_name", ["ridge", "linear"])
def test_make_sklearn_model_supports_ridge_and_linear(model_name: str) -> None:
    _require_sklearn()

    model = make_sklearn_model(model_name)

    assert list(model.named_steps) == ["imputer", "scaler", "model"]
    if model_name == "ridge":
        assert model.named_steps["model"].alpha == pytest.approx(1.0)
    else:
        assert model.named_steps["model"].__class__.__name__ == "LinearRegression"


def test_make_sklearn_model_supports_random_forest() -> None:
    _require_sklearn()

    model = make_sklearn_model("random_forest", random_state=7)

    assert list(model.named_steps) == ["imputer", "model"]
    assert model.named_steps["model"].n_estimators == 100
    assert model.named_steps["model"].random_state == 7


def test_train_predict_window_writes_expected_prediction_columns() -> None:
    _require_sklearn()

    train_df = _make_window_frame("2000-01-31", 12, window_offset=0)
    test_df = _make_window_frame("2001-01-31", 6, window_offset=1)

    predictions, metrics = train_predict_window(
        train_df,
        test_df,
        window_id="train_2000-2000_test_2001",
        model_name="ridge",
    )

    required = {"window_id", "model_name", "asset_id", "date", "predicted_return", "forward_1m_total_ret"}
    assert required.issubset(set(predictions.columns))
    assert len(predictions) == len(test_df)
    assert predictions["window_id"].nunique() == 1
    assert metrics["window_id"] == "train_2000-2000_test_2001"
    assert metrics["model_name"] == "ridge"
    assert metrics["train_rows"] == len(train_df)
    assert metrics["test_rows"] == len(test_df)
    assert metrics["prediction_rows"] == len(test_df)
    assert metrics["mse"] is not None
    assert metrics["mae"] is not None
    assert metrics["prediction_ic"] is not None
    assert metrics["prediction_rank_ic"] is not None


def test_train_predict_window_metrics_are_deterministic() -> None:
    _require_sklearn()

    train_df = _make_window_frame("2000-01-31", 12, window_offset=0)
    test_df = _make_window_frame("2001-01-31", 6, window_offset=1)

    predictions1, metrics1 = train_predict_window(
        train_df,
        test_df,
        window_id="train_2000-2000_test_2001",
        model_name="ridge",
    )
    predictions2, metrics2 = train_predict_window(
        train_df,
        test_df,
        window_id="train_2000-2000_test_2001",
        model_name="ridge",
    )

    pd.testing.assert_frame_equal(predictions1, predictions2)
    assert metrics1 == metrics2


def test_prediction_portfolio_ranks_by_predicted_return_and_skips_small_months() -> None:
    frame = pd.DataFrame(
        {
            "date": [
                pd.Timestamp("2021-01-31"),
                pd.Timestamp("2021-01-31"),
                pd.Timestamp("2021-01-31"),
                pd.Timestamp("2021-01-31"),
                pd.Timestamp("2021-02-28"),
            ],
            "asset_id": ["A", "B", "C", "D", "E"],
            "predicted_return": [0.10, 0.20, 0.30, 0.40, 0.50],
            "forward_1m_total_ret": [0.01, 0.02, 0.03, 0.04, 0.05],
        }
    )

    portfolio = build_prediction_portfolio_returns(frame, quantile=0.25)

    assert portfolio["date"].tolist() == [pd.Timestamp("2021-01-31")]
    assert portfolio.iloc[0]["long_ret"] == pytest.approx(0.04)
    assert portfolio.iloc[0]["short_ret"] == pytest.approx(0.01)
    assert portfolio.iloc[0]["long_short_ret"] == pytest.approx(0.03)
    assert portfolio.iloc[0]["long_count"] == 1
    assert portfolio.iloc[0]["short_count"] == 1
    assert portfolio.iloc[0]["quantile"] == pytest.approx(0.25)


def test_summarize_prediction_portfolio_metrics_are_deterministic() -> None:
    portfolio = pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-31"), pd.Timestamp("2024-02-29")],
            "long_short_ret": [0.10, 0.05],
        }
    )

    summary = summarize_prediction_portfolio(portfolio)

    cumulative_factor = 1.10 * 1.05
    expected_std = pd.Series([0.10, 0.05]).std(ddof=1)
    expected_annualized_return = cumulative_factor ** (12.0 / 2.0) - 1.0
    expected_annualized_volatility = expected_std * math.sqrt(12.0)

    assert summary["rows"] == 2
    assert summary["date_min"] == "2024-01-31"
    assert summary["date_max"] == "2024-02-29"
    assert summary["cumulative_return"] == pytest.approx(cumulative_factor - 1.0)
    assert summary["annualized_return"] == pytest.approx(expected_annualized_return)
    assert summary["annualized_volatility"] == pytest.approx(expected_annualized_volatility)
    assert summary["sharpe"] == pytest.approx(expected_annualized_return / expected_annualized_volatility)
    assert summary["mean_monthly_return"] == pytest.approx(0.075)
    assert summary["std_monthly_return"] == pytest.approx(expected_std)
    assert summary["positive_month_ratio"] == pytest.approx(1.0)
    assert summary["worst_month"] == pytest.approx(0.05)
    assert summary["best_month"] == pytest.approx(0.10)


def test_run_walk_forward_sklearn_baseline_discovers_multiple_windows(tmp_path: Path) -> None:
    _require_sklearn()

    splits_dir = _write_splits_dir(tmp_path)
    result = run_walk_forward_sklearn_baseline(
        splits_dir,
        model_name="ridge",
        quantile=0.25,
        random_state=0,
    )

    predictions = result["predictions"]
    window_metrics = result["window_metrics"]
    portfolio = result["portfolio_returns"]
    summary = result["summary"]

    assert summary["status"] == "ok"
    assert summary["stage"] == "crsp_sklearn_baseline"
    assert summary["model_name"] == "ridge"
    assert summary["windows"] == 2
    assert summary["prediction_rows"] == len(predictions)
    assert summary["portfolio_rows"] == len(portfolio)
    assert summary["average_mse"] is not None
    assert summary["average_mae"] is not None
    assert summary["average_prediction_ic"] is not None
    assert summary["average_prediction_rank_ic"] is not None
    assert len(window_metrics) == 2
    assert predictions["window_id"].nunique() == 2
    assert predictions["model_name"].nunique() == 1
    assert portfolio["date"].nunique() > 0


def test_run_walk_forward_sklearn_baseline_cli_writes_expected_artifacts(tmp_path: Path) -> None:
    _require_sklearn()

    splits_dir = _write_splits_dir(tmp_path)
    output_dir = tmp_path / "crsp_sklearn_baseline"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--splits-dir",
            str(splits_dir),
            "--output-dir",
            str(output_dir),
            "--model",
            "ridge",
            "--quantile",
            "0.25",
            "--random-state",
            "0",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / "predictions.parquet").exists()
    assert (output_dir / "window_metrics.json").exists()
    assert (output_dir / "prediction_portfolio_returns.parquet").exists()
    assert (output_dir / "summary.json").exists()

    stdout_summary = json.loads(result.stdout)
    file_summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    window_metrics = json.loads((output_dir / "window_metrics.json").read_text(encoding="utf-8"))
    predictions = pd.read_parquet(output_dir / "predictions.parquet")
    portfolio = pd.read_parquet(output_dir / "prediction_portfolio_returns.parquet")

    assert stdout_summary == file_summary
    assert file_summary["status"] == "ok"
    assert file_summary["model_name"] == "ridge"
    assert file_summary["windows"] == 2
    assert file_summary["prediction_rows"] == len(predictions)
    assert file_summary["portfolio_rows"] == len(portfolio)
    assert window_metrics["status"] == "ok"
    assert window_metrics["window_count"] == 2
    assert len(window_metrics["window_metrics"]) == 2
    assert {"window_id", "predicted_return", "forward_1m_total_ret"}.issubset(set(predictions.columns))
    assert {"date", "long_short_ret", "quantile"}.issubset(set(portfolio.columns))


def test_run_walk_forward_sklearn_baseline_cli_accepts_feature_columns_json(tmp_path: Path) -> None:
    _require_sklearn()

    splits_dir = _write_splits_dir(tmp_path)
    output_dir = tmp_path / "crsp_sklearn_baseline_json"
    feature_columns_json = tmp_path / "feature_columns.json"
    selected_feature_cols = ["mom12_1", "mom6_1"]
    write_feature_columns_json(feature_columns_json, selected_feature_cols)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--splits-dir",
            str(splits_dir),
            "--output-dir",
            str(output_dir),
            "--model",
            "ridge",
            "--quantile",
            "0.25",
            "--random-state",
            "0",
            "--feature-columns-json",
            str(feature_columns_json),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode == 0, result.stderr

    file_summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    window_metrics = json.loads((output_dir / "window_metrics.json").read_text(encoding="utf-8"))

    assert file_summary["feature_cols"] == selected_feature_cols
    assert window_metrics["feature_cols"] == selected_feature_cols
    assert file_summary["windows"] == 2
    assert window_metrics["window_count"] == 2
