from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .ml_dataset import build_ml_dataset, infer_ml_feature_cols, time_train_test_split

SUPPORTED_MODELS = {
    "ridge_regressor",
    "random_forest_regressor",
    "hist_gradient_boosting_regressor",
}


def _require_sklearn() -> None:
    try:
        import sklearn  # noqa: F401
    except ImportError:
        raise ImportError(
            "scikit-learn is required for sklearn model adapters.\n"
            'Install with: python3 -m pip install -e ".[sklearn]"'
        ) from None


def _make_model(model_name: str, *, random_state: int = 42):
    _require_sklearn()
    if model_name == "ridge_regressor":
        from sklearn.linear_model import Ridge
        return Ridge(random_state=random_state)
    if model_name == "random_forest_regressor":
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(random_state=random_state)
    if model_name == "hist_gradient_boosting_regressor":
        from sklearn.ensemble import HistGradientBoostingRegressor
        return HistGradientBoostingRegressor(random_state=random_state)
    raise ValueError(
        f"Unsupported model name: {model_name}. "
        f"Supported: {', '.join(sorted(SUPPORTED_MODELS))}"
    )


def _preprocess(
    train_df: pd.DataFrame,
    *,
    feature_cols: list[str],
    label_col: str,
    standardize: bool,
) -> dict:
    X_train = train_df[feature_cols].copy().astype(float)
    y_train = train_df[label_col].copy().astype(float)

    medians = X_train.median().fillna(0.0)
    X_filled = X_train.fillna(medians)

    means = X_filled.mean().fillna(0.0)
    stds = X_filled.std(ddof=0).replace(0.0, 1.0).fillna(1.0)

    if standardize:
        X_proc = ((X_filled - means) / stds).values
    else:
        X_proc = X_filled.values

    return {
        "X": X_proc,
        "y": y_train.values if not y_train.isna().any() else y_train.fillna(0.0).values,
        "medians": medians,
        "means": means,
        "stds": stds,
        "standardize": standardize,
    }


def _preprocess_predict(
    df: pd.DataFrame,
    *,
    feature_cols: list[str],
    preproc: dict,
) -> np.ndarray:
    X = df[feature_cols].copy().astype(float)
    X_filled = X.fillna(preproc["medians"])
    if preproc["standardize"]:
        X_proc = ((X_filled - preproc["means"]) / preproc["stds"]).values
    else:
        X_proc = X_filled.values
    return X_proc


def _extract_ridge_coefficients(model) -> dict[str, float]:
    return dict(zip(["intercept"], [model.intercept_])) | {
        f"coef_{i}": float(v) for i, v in enumerate(model.coef_)
    }


def _extract_feature_importance(
    model,
    feature_cols: list[str],
    model_name: str,
) -> pd.DataFrame:
    importance_values: list[float | None] = []
    importance_type = "none"

    if model_name == "ridge_regressor":
        importance_values = [float(v) for v in model.coef_]
        importance_type = "coefficient"
    elif hasattr(model, "feature_importances_"):
        importance_values = [float(v) for v in model.feature_importances_]
        importance_type = "feature_importances_"
    else:
        importance_values = [None] * len(feature_cols)

    return pd.DataFrame({
        "feature": feature_cols,
        "importance": importance_values,
        "importance_type": importance_type,
        "model_name": model_name,
    })


def fit_sklearn_model(
    train_df: pd.DataFrame,
    *,
    model_name: str,
    feature_cols: list[str],
    label_col: str,
    random_state: int = 42,
) -> dict:
    if model_name not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unsupported model name: {model_name}. "
            f"Supported: {', '.join(sorted(SUPPORTED_MODELS))}"
        )

    if not feature_cols:
        raise ValueError("At least one ML feature column is required")

    _require_sklearn()

    standardize = (model_name == "ridge_regressor")
    preproc = _preprocess(
        train_df,
        feature_cols=feature_cols,
        label_col=label_col,
        standardize=standardize,
    )

    model = _make_model(model_name, random_state=random_state)
    model.fit(preproc["X"], preproc["y"])

    return {
        "model": model,
        "model_name": model_name,
        "feature_cols": feature_cols,
        "label_col": label_col,
        "preproc": preproc,
        "train_row_count": int(len(train_df)),
    }


def predict_sklearn_model(
    model_pack: dict,
    dataset_df: pd.DataFrame,
    *,
    prediction_col: str = "predicted_return",
    asset_id_col: str = "asset_id",
    date_col: str = "date",
) -> pd.DataFrame:
    feature_cols = model_pack["feature_cols"]
    preproc = model_pack["preproc"]

    X_pred = _preprocess_predict(dataset_df, feature_cols=feature_cols, preproc=preproc)
    predictions = model_pack["model"].predict(X_pred)

    label_col = model_pack.get("label_col", "ret_fwd_1m")
    result = pd.DataFrame({
        "asset_id": dataset_df[asset_id_col].values,
        "date": dataset_df[date_col].values,
        prediction_col: predictions,
        "model_name": model_pack["model_name"],
    })

    if label_col in dataset_df.columns:
        result[label_col] = dataset_df[label_col].values

    return result


def evaluate_sklearn_predictions(
    predictions_df: pd.DataFrame,
    *,
    label_col: str = "ret_fwd_1m",
    prediction_col: str = "predicted_return",
) -> dict:
    if label_col not in predictions_df.columns:
        return {
            "row_count": len(predictions_df),
            "error": f"label column '{label_col}' not found in predictions",
        }

    y_true = pd.to_numeric(predictions_df[label_col], errors="coerce")
    y_pred = pd.to_numeric(predictions_df[prediction_col], errors="coerce")
    mask = y_true.notna() & y_pred.notna()
    y_true = y_true[mask].values
    y_pred = y_pred[mask].values
    row_count = len(y_true)

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

    if row_count >= 2:
        std_pred = np.std(y_pred, ddof=0)
        std_true = np.std(y_true, ddof=0)
        if std_pred > 0 and std_true > 0:
            result["prediction_label_correlation"] = float(np.corrcoef(y_pred, y_true)[0, 1])

    return result


def write_artifacts(
    output_dir: Path,
    *,
    model_pack: dict,
    predictions: pd.DataFrame,
    metrics: dict,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    train_config: dict,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    predictions_path = output_dir / "predictions.csv"
    predictions.to_csv(predictions_path, index=False)

    metrics_path = output_dir / "metrics.json"
    metrics_full = {
        **metrics,
        "train_row_count": model_pack["train_row_count"],
        "test_row_count": int(len(test_df)),
    }
    with open(metrics_path, "w") as f:
        json.dump(metrics_full, f, indent=2, default=str)

    fi = _extract_feature_importance(
        model_pack["model"],
        model_pack["feature_cols"],
        model_pack["model_name"],
    )
    fi_path = output_dir / "feature_importance.csv"
    fi.to_csv(fi_path, index=False)

    summary = {
        "model_name": model_pack["model_name"],
        "model_type": model_pack["model_name"],
        "feature_cols": model_pack["feature_cols"],
        "label_col": model_pack["label_col"],
        "train_end": train_config.get("train_end", None),
        "train_row_count": model_pack["train_row_count"],
        "test_row_count": int(len(test_df)),
        "sklearn_required": True,
    }
    summary_path = output_dir / "model_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    config_path = output_dir / "train_config.json"
    with open(config_path, "w") as f:
        json.dump(train_config, f, indent=2, default=str)

    return {
        "predictions": predictions_path,
        "metrics": metrics_path,
        "feature_importance": fi_path,
        "model_summary": summary_path,
        "train_config": config_path,
    }


def run_sklearn_ml_model(
    panel_df: pd.DataFrame,
    *,
    model_name: str,
    output_dir: Path,
    label_col: str = "ret_fwd_1m",
    train_end: str,
    feature_cols: list[str] | None = None,
    asset_id_col: str = "asset_id",
    date_col: str = "date",
    random_state: int = 42,
) -> dict[str, Path]:
    _require_sklearn()

    if feature_cols is None:
        feature_cols = infer_ml_feature_cols(
            panel_df,
            asset_id_col=asset_id_col,
            date_col=date_col,
            label_col=label_col,
        )

    if not feature_cols:
        raise ValueError("At least one ML feature column is required")

    dataset = build_ml_dataset(
        panel_df,
        asset_id_col=asset_id_col,
        date_col=date_col,
        label_col=label_col,
        feature_cols=feature_cols,
        drop_missing_label=True,
        drop_missing_features=False,
    )

    train_df, test_df = time_train_test_split(
        dataset,
        date_col=date_col,
        train_end=train_end,
    )

    model_pack = fit_sklearn_model(
        train_df,
        model_name=model_name,
        feature_cols=feature_cols,
        label_col=label_col,
        random_state=random_state,
    )

    predictions = predict_sklearn_model(
        model_pack,
        test_df,
        asset_id_col=asset_id_col,
        date_col=date_col,
    )

    metrics = evaluate_sklearn_predictions(
        predictions,
        label_col=label_col,
    )

    train_config = {
        "model_name": model_name,
        "label_col": label_col,
        "train_end": train_end,
        "feature_cols": feature_cols,
        "asset_id_col": asset_id_col,
        "date_col": date_col,
        "random_state": random_state,
    }

    return write_artifacts(
        output_dir,
        model_pack=model_pack,
        predictions=predictions,
        metrics=metrics,
        train_df=train_df,
        test_df=test_df,
        train_config=train_config,
    )
