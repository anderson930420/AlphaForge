from __future__ import annotations

import numpy as np
import pandas as pd


def fit_baseline_regressor(
    train_df: pd.DataFrame,
    *,
    feature_cols: list[str],
    label_col: str,
    alpha: float = 1.0,
) -> object:
    X = train_df[feature_cols].copy().astype(float)
    y = train_df[label_col].copy().astype(float)

    medians = X.median().fillna(0.0)
    X_filled = X.fillna(medians)

    means = X_filled.mean().fillna(0.0)
    stds = X_filled.std(ddof=0).replace(0.0, 1.0).fillna(1.0)
    X_scaled = (X_filled - means) / stds

    n = len(X_scaled)
    X_design = np.column_stack([np.ones(n), X_scaled])
    XtX = X_design.T @ X_design
    ridge = alpha * np.eye(X_design.shape[1])
    ridge[0, 0] = 0.0
    coef = np.linalg.solve(XtX + ridge, X_design.T @ y)

    return {
        "medians": medians,
        "means": means,
        "stds": stds,
        "coef": coef,
        "feature_cols": feature_cols,
        "intercept": coef[0],
        "weights": coef[1:],
        "alpha": alpha,
    }


def predict_baseline_regressor(
    model: object,
    dataset_df: pd.DataFrame,
    *,
    feature_cols: list[str],
    prediction_col: str = "predicted_return",
    label_col: str | None = None,
    asset_id_col: str = "asset_id",
    date_col: str = "date",
) -> pd.DataFrame:
    m = model
    X = dataset_df[feature_cols].copy().astype(float)
    X_filled = X.fillna(m["medians"])
    X_scaled = (X_filled - m["means"]) / m["stds"]
    n = len(X_scaled)
    X_design = np.column_stack([np.ones(n), X_scaled])
    predictions = X_design @ m["coef"]

    result = pd.DataFrame({
        "asset_id": dataset_df[asset_id_col].values,
        "date": dataset_df[date_col].values,
        prediction_col: predictions,
    })

    label_col_names = [c for c in dataset_df.columns if c.startswith("ret_fwd")]
    for col in label_col_names:
        if col in dataset_df.columns and col != prediction_col:
            result[col] = dataset_df[col].values
    if label_col is not None and label_col in dataset_df.columns and label_col not in result.columns:
        result[label_col] = dataset_df[label_col].values

    return result


def evaluate_regression_predictions(
    predictions_df: pd.DataFrame,
    *,
    label_col: str = "ret_fwd_1m",
    prediction_col: str = "predicted_return",
) -> dict:
    if label_col not in predictions_df.columns:
        return {"row_count": len(predictions_df), "error": f"label column '{label_col}' not found in predictions"}

    y_true = pd.to_numeric(predictions_df[label_col], errors="coerce")
    y_pred = pd.to_numeric(predictions_df[prediction_col], errors="coerce")
    mask = y_true.notna() & y_pred.notna()
    y_true = y_true[mask].values
    y_pred = y_pred[mask].values
    row_count = len(y_true)

    if row_count < 2:
        result: dict = {
            "row_count": int(row_count),
            "mean_prediction": float(np.nanmean(predictions_df[prediction_col]) if len(predictions_df) > 0 else np.nan),
            "mean_label": float(np.nanmean(predictions_df[label_col]) if len(predictions_df) > 0 else np.nan),
        }
        if row_count == 0:
            return result
        errors = y_true - y_pred
        result["mse"] = float(np.mean(errors ** 2))
        result["mae"] = float(np.mean(np.abs(errors)))
        return result

    errors = y_true - y_pred
    mse = float(np.mean(errors ** 2))
    mae = float(np.mean(np.abs(errors)))

    std_pred = np.std(y_pred, ddof=0)
    std_true = np.std(y_true, ddof=0)
    correlation = np.nan
    if std_pred > 0 and std_true > 0:
        correlation = float(np.corrcoef(y_pred, y_true)[0, 1])

    return {
        "row_count": int(row_count),
        "mse": mse,
        "mae": mae,
        "correlation": correlation,
        "mean_prediction": float(np.mean(y_pred)),
        "mean_label": float(np.mean(y_true)),
    }
