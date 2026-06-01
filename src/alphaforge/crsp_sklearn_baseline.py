"""CRSP walk-forward sklearn baseline helpers.

This module trains a separate optional sklearn regression model per existing
CRSP ML walk-forward split, generates test-set predictions, and derives a
prediction-ranked long-short portfolio series. It does not alter CRSP dataset
construction, feature engineering, or walk-forward splitting.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from .json_utils import json_safe_float
from .ml_diagnostics import run_ml_prediction_diagnostics
from .parquet_io import read_parquet_artifact


DEFAULT_CRSP_SKLEARN_FEATURE_COLUMNS = [
    "mom12_1",
    "mom6_1",
    "mom3_1",
    "ret1_0",
    "volatility_12m",
    "turnover",
    "log_market_cap",
    "log_price",
]

SUPPORTED_CRSP_SKLEARN_MODELS = ("ridge", "linear", "random_forest")

_ASSET_ID_COLUMN = "asset_id"
_DATE_COLUMN = "date"
_PREDICTION_COLUMN = "predicted_return"


def require_sklearn() -> None:
    """Raise a clear error when scikit-learn is unavailable."""
    try:
        import sklearn  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised through skip-aware tests
        raise ImportError(
            "scikit-learn is required for the CRSP sklearn baseline.\n"
            'Install with: python3 -m pip install -e ".[sklearn]"'
        ) from exc


def make_sklearn_model(
    model_name: str = "ridge",
    *,
    random_state: int = 0,
):
    """Build a deterministic sklearn regression pipeline."""
    if model_name not in SUPPORTED_CRSP_SKLEARN_MODELS:
        raise ValueError(
            f"Unsupported model name: {model_name}. "
            f"Supported: {', '.join(SUPPORTED_CRSP_SKLEARN_MODELS)}"
        )

    require_sklearn()

    from sklearn.ensemble import RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    if model_name == "ridge":
        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=1.0)),
            ]
        )

    if model_name == "linear":
        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LinearRegression()),
            ]
        )

    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=100,
                    max_depth=5,
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def validate_training_frame(
    df: pd.DataFrame,
    *,
    feature_cols: list[str],
    label_col: str,
) -> None:
    """Validate that a CRSP walk-forward frame is structurally fit for training."""
    _prepare_window_frame(
        df,
        feature_cols=feature_cols,
        label_col=label_col,
        frame_name="training frame",
        require_label=True,
    )


def train_predict_window(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    *,
    window_id: str,
    feature_cols: list[str] | None = None,
    label_col: str = "forward_1m_total_ret",
    model_name: str = "ridge",
    random_state: int = 0,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Train a sklearn model on one walk-forward window and predict its test split."""
    if feature_cols is None:
        feature_cols = list(DEFAULT_CRSP_SKLEARN_FEATURE_COLUMNS)
    if not feature_cols:
        raise ValueError("feature_cols must not be empty")

    train_frame = _prepare_window_frame(
        train_df,
        feature_cols=feature_cols,
        label_col=label_col,
        frame_name="training frame",
        require_label=True,
    )
    test_frame = _prepare_window_frame(
        test_df,
        feature_cols=feature_cols,
        label_col=label_col,
        frame_name="test frame",
        require_label=True,
    )

    train_model_frame = train_frame.loc[train_frame[label_col].notna()].copy()
    train_missing_label_rows = int(len(train_frame) - len(train_model_frame))
    if train_model_frame.empty:
        raise ValueError("Training frame has no rows with a non-missing label")

    model = make_sklearn_model(model_name, random_state=random_state)
    model.fit(train_model_frame[feature_cols], train_model_frame[label_col])

    predictions = model.predict(test_frame[feature_cols])
    prediction_frame = pd.DataFrame(
        {
            "window_id": window_id,
            "model_name": model_name,
            _ASSET_ID_COLUMN: test_frame[_ASSET_ID_COLUMN].values,
            _DATE_COLUMN: test_frame[_DATE_COLUMN].values,
            _PREDICTION_COLUMN: predictions,
            label_col: test_frame[label_col].values,
        }
    )
    prediction_frame = prediction_frame.sort_values(
        [_DATE_COLUMN, _ASSET_ID_COLUMN],
        kind="mergesort",
    ).reset_index(drop=True)

    diagnostics = run_ml_prediction_diagnostics(
        prediction_frame,
        prediction_col=_PREDICTION_COLUMN,
        label_col=label_col,
        asset_id_col=_ASSET_ID_COLUMN,
        date_col=_DATE_COLUMN,
    )
    diagnostics_summary = diagnostics.summary

    metrics = {
        "window_id": window_id,
        "model_name": model_name,
        "feature_cols": list(feature_cols),
        "label_col": label_col,
        "train_rows": int(len(train_frame)),
        "train_rows_used": int(len(train_model_frame)),
        "train_missing_label_rows": train_missing_label_rows,
        "test_rows": int(len(test_frame)),
        "prediction_rows": int(len(prediction_frame)),
        "valid_prediction_rows": int(diagnostics_summary.get("valid_row_count", 0)),
        "date_min": diagnostics_summary.get("date_min"),
        "date_max": diagnostics_summary.get("date_max"),
        "train_date_min": _date_to_iso(train_frame[_DATE_COLUMN].min()),
        "train_date_max": _date_to_iso(train_frame[_DATE_COLUMN].max()),
        "test_date_min": _date_to_iso(test_frame[_DATE_COLUMN].min()),
        "test_date_max": _date_to_iso(test_frame[_DATE_COLUMN].max()),
        "asset_count": int(test_frame[_ASSET_ID_COLUMN].nunique(dropna=True)),
        "date_count": int(test_frame[_DATE_COLUMN].nunique(dropna=True)),
        "mse": diagnostics_summary.get("overall_mse"),
        "mae": diagnostics_summary.get("overall_mae"),
        "prediction_ic": diagnostics_summary.get("prediction_ic_mean"),
        "prediction_rank_ic": diagnostics_summary.get("prediction_rank_ic_mean"),
        "prediction_ic_observation_count": diagnostics_summary.get("prediction_ic_observation_count"),
        "prediction_rank_ic_observation_count": diagnostics_summary.get("prediction_rank_ic_observation_count"),
    }

    return prediction_frame, metrics


def build_prediction_portfolio_returns(
    predictions: pd.DataFrame,
    *,
    prediction_col: str = _PREDICTION_COLUMN,
    label_col: str = "forward_1m_total_ret",
    quantile: float = 0.1,
) -> pd.DataFrame:
    """Build a top-minus-bottom portfolio from cross-sectional predictions."""
    _validate_prediction_portfolio_input(
        predictions,
        prediction_col=prediction_col,
        label_col=label_col,
        quantile=quantile,
    )

    frame = predictions.copy()
    frame[_DATE_COLUMN] = pd.to_datetime(frame[_DATE_COLUMN], errors="coerce")
    if frame[_DATE_COLUMN].isna().any():
        raise ValueError("date must be parseable as datetime")
    if frame[_ASSET_ID_COLUMN].isna().any():
        raise ValueError("asset_id must be non-null")

    frame[_ASSET_ID_COLUMN] = frame[_ASSET_ID_COLUMN].astype(str)
    frame = frame.sort_values([_ASSET_ID_COLUMN, _DATE_COLUMN], kind="mergesort").reset_index(drop=True)
    frame[prediction_col] = pd.to_numeric(frame[prediction_col], errors="coerce")
    frame[label_col] = pd.to_numeric(frame[label_col], errors="coerce")

    output_rows: list[dict[str, object]] = []
    for date_value, date_frame in frame.groupby(_DATE_COLUMN, sort=True):
        valid_mask = date_frame[prediction_col].notna() & date_frame[label_col].notna()
        if not valid_mask.any():
            continue

        ranked = date_frame.loc[valid_mask].copy()
        ranked["_asset_id_sort"] = ranked[_ASSET_ID_COLUMN].astype(str)
        ranked = ranked.sort_values(
            by=[prediction_col, "_asset_id_sort"],
            ascending=[True, True],
            kind="mergesort",
        ).reset_index(drop=True)

        side_count = int(math.ceil(len(ranked) * quantile))
        side_count = min(side_count, len(ranked) // 2)
        if side_count < 1:
            continue

        short_frame = ranked.iloc[:side_count].copy()
        long_frame = ranked.iloc[-side_count:].copy()

        long_ret = float(long_frame[label_col].mean())
        short_ret = float(short_frame[label_col].mean())

        output_rows.append(
            {
                "date": pd.Timestamp(date_value),
                "long_ret": float(long_ret),
                "short_ret": float(short_ret),
                "long_short_ret": float(long_ret - short_ret),
                "long_count": int(len(long_frame)),
                "short_count": int(len(short_frame)),
                "quantile": float(quantile),
            }
        )

    output_columns = [
        "date",
        "long_ret",
        "short_ret",
        "long_short_ret",
        "long_count",
        "short_count",
        "quantile",
    ]
    if not output_rows:
        return pd.DataFrame(columns=output_columns)
    return pd.DataFrame(output_rows, columns=output_columns)


def summarize_prediction_portfolio(portfolio_returns: pd.DataFrame) -> dict[str, object]:
    """Summarize a prediction-ranked long-short portfolio with deterministic formulas."""
    _validate_prediction_portfolio_summary_input(portfolio_returns)

    frame = portfolio_returns.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if frame["date"].isna().any():
        raise ValueError("date must be parseable as datetime")

    returns = pd.to_numeric(frame["long_short_ret"], errors="coerce").to_numpy(dtype=float, copy=True)
    returns[~np.isfinite(returns)] = np.nan
    valid_returns = returns[~np.isnan(returns)]
    if len(valid_returns) == 0:
        return {
            "rows": 0,
            "date_min": None,
            "date_max": None,
            "cumulative_return": None,
            "annualized_return": None,
            "annualized_volatility": None,
            "sharpe": None,
            "mean_monthly_return": None,
            "std_monthly_return": None,
            "positive_month_ratio": None,
            "worst_month": None,
            "best_month": None,
        }

    cumulative_factor = float(np.prod(1.0 + valid_returns))
    cumulative_return = cumulative_factor - 1.0

    if cumulative_factor > 0.0:
        annualized_return = float(cumulative_factor ** (12.0 / len(valid_returns)) - 1.0)
    else:
        annualized_return = None

    if len(valid_returns) < 2:
        monthly_std = 0.0
    else:
        monthly_std = float(np.std(valid_returns, ddof=1))
        if not np.isfinite(monthly_std):
            monthly_std = 0.0
    annualized_volatility = float(monthly_std * math.sqrt(12.0))
    sharpe = None
    if annualized_return is not None and not math.isclose(annualized_volatility, 0.0):
        sharpe = float(annualized_return / annualized_volatility)

    valid_dates = frame.loc[~np.isnan(returns), "date"]
    return {
        "rows": int(len(valid_returns)),
        "date_min": _date_to_iso(valid_dates.min()),
        "date_max": _date_to_iso(valid_dates.max()),
        "cumulative_return": json_safe_float(cumulative_return),
        "annualized_return": json_safe_float(annualized_return),
        "annualized_volatility": json_safe_float(annualized_volatility),
        "sharpe": json_safe_float(sharpe),
        "mean_monthly_return": json_safe_float(float(np.mean(valid_returns))),
        "std_monthly_return": json_safe_float(float(monthly_std)),
        "positive_month_ratio": json_safe_float(float((valid_returns > 0).mean())),
        "worst_month": json_safe_float(float(np.min(valid_returns))),
        "best_month": json_safe_float(float(np.max(valid_returns))),
    }


def run_walk_forward_sklearn_baseline(
    splits_dir: str | Path,
    *,
    model_name: str = "ridge",
    feature_cols: list[str] | None = None,
    label_col: str = "forward_1m_total_ret",
    quantile: float = 0.1,
    random_state: int = 0,
) -> dict[str, object]:
    """Train and evaluate a sklearn model across existing walk-forward splits."""
    require_sklearn()

    splits_path = Path(splits_dir)
    window_dirs = _discover_window_dirs(splits_path)
    if not window_dirs:
        raise ValueError(f"No walk-forward split directories found under {splits_path}")

    if feature_cols is None:
        resolved_feature_cols = list(DEFAULT_CRSP_SKLEARN_FEATURE_COLUMNS)
    else:
        resolved_feature_cols = list(feature_cols)
    if not resolved_feature_cols:
        raise ValueError("feature_cols must not be empty")

    prediction_frames: list[pd.DataFrame] = []
    window_metrics: list[dict[str, object]] = []

    for window_dir in window_dirs:
        train_path = window_dir / "train.parquet"
        test_path = window_dir / "test.parquet"
        if not train_path.exists() or not test_path.exists():
            raise ValueError(
                f"Walk-forward split directory is missing train.parquet or test.parquet: {window_dir}"
            )

        train_df = read_parquet_artifact(train_path)
        test_df = read_parquet_artifact(test_path)

        predictions, metrics = train_predict_window(
            train_df,
            test_df,
            window_id=window_dir.name,
            feature_cols=resolved_feature_cols,
            label_col=label_col,
            model_name=model_name,
            random_state=random_state,
        )
        prediction_frames.append(predictions)
        window_metrics.append(metrics)

    predictions_df = pd.concat(prediction_frames, ignore_index=True) if prediction_frames else _empty_predictions_frame(label_col)
    if not predictions_df.empty:
        predictions_df = predictions_df.sort_values(
            ["date", "window_id", "asset_id"],
            kind="mergesort",
        ).reset_index(drop=True)

    portfolio_returns = build_prediction_portfolio_returns(
        predictions_df,
        prediction_col=_PREDICTION_COLUMN,
        label_col=label_col,
        quantile=quantile,
    )

    portfolio_summary = summarize_prediction_portfolio(portfolio_returns)
    prediction_date_min = _date_to_iso(pd.to_datetime(predictions_df["date"], errors="coerce").min()) if not predictions_df.empty else None
    prediction_date_max = _date_to_iso(pd.to_datetime(predictions_df["date"], errors="coerce").max()) if not predictions_df.empty else None

    summary = {
        "status": "ok",
        "stage": "crsp_sklearn_baseline",
        "splits_dir": str(splits_path),
        "model_name": model_name,
        "feature_cols": resolved_feature_cols,
        "label_col": label_col,
        "quantile": float(quantile),
        "random_state": int(random_state),
        "windows": int(len(window_metrics)),
        "window_ids": [metric["window_id"] for metric in window_metrics],
        "prediction_rows": int(len(predictions_df)),
        "date_min": prediction_date_min,
        "date_max": prediction_date_max,
        "average_mse": _mean_or_none(metric.get("mse") for metric in window_metrics),
        "average_mae": _mean_or_none(metric.get("mae") for metric in window_metrics),
        "average_prediction_ic": _mean_or_none(metric.get("prediction_ic") for metric in window_metrics),
        "average_prediction_rank_ic": _mean_or_none(metric.get("prediction_rank_ic") for metric in window_metrics),
        "portfolio_rows": portfolio_summary["rows"],
        "portfolio_date_min": portfolio_summary["date_min"],
        "portfolio_date_max": portfolio_summary["date_max"],
        "cumulative_return": portfolio_summary["cumulative_return"],
        "annualized_return": portfolio_summary["annualized_return"],
        "annualized_volatility": portfolio_summary["annualized_volatility"],
        "sharpe": portfolio_summary["sharpe"],
        "mean_monthly_return": portfolio_summary["mean_monthly_return"],
        "std_monthly_return": portfolio_summary["std_monthly_return"],
        "positive_month_ratio": portfolio_summary["positive_month_ratio"],
        "worst_month": portfolio_summary["worst_month"],
        "best_month": portfolio_summary["best_month"],
    }

    return {
        "predictions": predictions_df,
        "window_metrics": window_metrics,
        "portfolio_returns": portfolio_returns,
        "summary": summary,
    }


def _prepare_window_frame(
    df: pd.DataFrame,
    *,
    feature_cols: list[str],
    label_col: str,
    frame_name: str,
    require_label: bool,
) -> pd.DataFrame:
    required_columns = [_ASSET_ID_COLUMN, _DATE_COLUMN, *feature_cols]
    if require_label:
        required_columns.append(label_col)

    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if not feature_cols:
        raise ValueError("feature_cols must not be empty")

    frame = df.copy()
    frame[_DATE_COLUMN] = pd.to_datetime(frame[_DATE_COLUMN], errors="coerce")
    if frame[_DATE_COLUMN].isna().any():
        invalid_values = frame.loc[frame[_DATE_COLUMN].isna(), _DATE_COLUMN].astype(str).head(5).tolist()
        raise ValueError(f"date must be parseable as datetime; invalid values: {invalid_values}")
    frame[_DATE_COLUMN] = (frame[_DATE_COLUMN] + pd.offsets.MonthEnd(0)).dt.normalize()

    if frame[_ASSET_ID_COLUMN].isna().any():
        raise ValueError("asset_id must be non-null")
    if frame[_ASSET_ID_COLUMN].astype("string").str.strip().eq("").any():
        raise ValueError("asset_id must be non-empty")
    frame[_ASSET_ID_COLUMN] = frame[_ASSET_ID_COLUMN].astype(str)

    if frame[[_ASSET_ID_COLUMN, _DATE_COLUMN]].duplicated().any():
        raise ValueError("duplicate asset_id/date rows are not allowed")

    for column in feature_cols:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if label_col in frame.columns:
        frame[label_col] = pd.to_numeric(frame[label_col], errors="coerce")
    elif require_label:
        raise ValueError(f"Missing required label column: {label_col!r}")

    return frame.sort_values([_DATE_COLUMN, _ASSET_ID_COLUMN], kind="mergesort").reset_index(drop=True)


def _discover_window_dirs(splits_path: Path) -> list[Path]:
    if not splits_path.exists():
        raise FileNotFoundError(f"Split directory does not exist: {splits_path}")

    window_dirs = [
        child
        for child in splits_path.iterdir()
        if child.is_dir() and (child / "train.parquet").exists() and (child / "test.parquet").exists()
    ]
    if not window_dirs and (splits_path / "train.parquet").exists() and (splits_path / "test.parquet").exists():
        window_dirs = [splits_path]

    return sorted(window_dirs, key=lambda path: path.name)


def _validate_prediction_portfolio_input(
    predictions: pd.DataFrame,
    *,
    prediction_col: str,
    label_col: str,
    quantile: float,
) -> None:
    required = {_ASSET_ID_COLUMN, _DATE_COLUMN, prediction_col, label_col}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if predictions.empty:
        raise ValueError("Prediction panel is empty")
    if not (0.0 < quantile <= 1.0):
        raise ValueError(f"quantile must be between 0 and 1, got {quantile}")


def _validate_prediction_portfolio_summary_input(portfolio_returns: pd.DataFrame) -> None:
    required = {"date", "long_short_ret"}
    missing = required - set(portfolio_returns.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")


def _mean_or_none(values) -> float | None:
    finite_values = [value for value in values if value is not None]
    if not finite_values:
        return None
    return json_safe_float(float(np.mean(finite_values)))


def _date_to_iso(value: pd.Timestamp | str | None) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()


def _empty_predictions_frame(label_col: str) -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "window_id",
            "model_name",
            _ASSET_ID_COLUMN,
            _DATE_COLUMN,
            _PREDICTION_COLUMN,
            label_col,
        ]
    )
