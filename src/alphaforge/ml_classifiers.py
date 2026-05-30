from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .json_utils import json_safe_float, write_json_artifact
from .ml_models import _require_sklearn


SUPPORTED_CLASSIFIERS = {
    "logistic_regression_classifier",
    "random_forest_classifier",
    "hist_gradient_boosting_classifier",
}


def _make_classifier(classifier_name: str, *, random_state: int = 42):
    _require_sklearn()
    if classifier_name == "logistic_regression_classifier":
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(random_state=random_state, max_iter=1000)
    if classifier_name == "random_forest_classifier":
        from sklearn.ensemble import RandomForestClassifier

        return RandomForestClassifier(random_state=random_state)
    if classifier_name == "hist_gradient_boosting_classifier":
        from sklearn.ensemble import HistGradientBoostingClassifier

        return HistGradientBoostingClassifier(random_state=random_state)
    raise ValueError(
        f"Unsupported classifier name: {classifier_name}. "
        f"Supported: {', '.join(sorted(SUPPORTED_CLASSIFIERS))}"
    )


def _preprocess(
    train_df: pd.DataFrame,
    *,
    feature_cols: list[str],
    label_col: str,
    standardize: bool,
) -> dict[str, Any]:
    X_train = train_df[feature_cols].copy().astype(float)
    y_train = train_df[label_col].copy().astype(int)
    medians = X_train.median().fillna(0.0)
    X_filled = X_train.fillna(medians)
    means = X_filled.mean().fillna(0.0)
    stds = X_filled.std(ddof=0).replace(0.0, 1.0).fillna(1.0)
    X_proc = ((X_filled - means) / stds).values if standardize else X_filled.values
    return {
        "X": X_proc,
        "y": y_train.values,
        "medians": medians,
        "means": means,
        "stds": stds,
        "standardize": standardize,
    }


def _preprocess_predict(
    df: pd.DataFrame,
    *,
    feature_cols: list[str],
    preproc: dict[str, Any],
) -> np.ndarray:
    X = df[feature_cols].copy().astype(float)
    X_filled = X.fillna(preproc["medians"])
    if preproc["standardize"]:
        return ((X_filled - preproc["means"]) / preproc["stds"]).values
    return X_filled.values


def fit_sklearn_classifier(
    train_df: pd.DataFrame,
    *,
    classifier_name: str,
    feature_cols: list[str],
    label_col: str,
    random_state: int = 42,
) -> dict[str, Any]:
    if classifier_name not in SUPPORTED_CLASSIFIERS:
        raise ValueError(
            f"Unsupported classifier name: {classifier_name}. "
            f"Supported: {', '.join(sorted(SUPPORTED_CLASSIFIERS))}"
        )
    if not feature_cols:
        raise ValueError("At least one ML feature column is required")
    if label_col not in train_df.columns:
        raise ValueError(f"label_col {label_col!r} not found in training data")

    y = pd.to_numeric(train_df[label_col], errors="coerce")
    valid_classes = sorted(y.dropna().astype(int).unique().tolist())
    if len(valid_classes) < 2:
        raise ValueError("Classifier training requires at least two classes")

    standardize = classifier_name == "logistic_regression_classifier"
    preproc = _preprocess(
        train_df,
        feature_cols=feature_cols,
        label_col=label_col,
        standardize=standardize,
    )
    model = _make_classifier(classifier_name, random_state=random_state)
    model.fit(preproc["X"], preproc["y"])
    return {
        "model": model,
        "classifier_name": classifier_name,
        "feature_cols": feature_cols,
        "label_col": label_col,
        "preproc": preproc,
        "classes": [int(value) for value in model.classes_.tolist()],
        "positive_class": 1 if 1 in set(model.classes_.tolist()) else int(model.classes_[-1]),
        "train_row_count": int(len(train_df)),
    }


def predict_sklearn_classifier(
    classifier_pack: dict[str, Any],
    dataset_df: pd.DataFrame,
    *,
    probability_col: str = "predicted_probability",
    prediction_col: str = "predicted_class",
    asset_id_col: str = "asset_id",
    date_col: str = "date",
) -> pd.DataFrame:
    feature_cols = classifier_pack["feature_cols"]
    preproc = classifier_pack["preproc"]
    model = classifier_pack["model"]
    X_pred = _preprocess_predict(dataset_df, feature_cols=feature_cols, preproc=preproc)
    predicted_class = model.predict(X_pred).astype(int)

    if not hasattr(model, "predict_proba"):
        raise ValueError("Classifier does not expose predict_proba")
    probabilities = model.predict_proba(X_pred)
    classes = [int(value) for value in model.classes_.tolist()]
    positive_class = int(classifier_pack["positive_class"])
    positive_idx = classes.index(positive_class)

    label_col = classifier_pack.get("label_col", "target")
    result = pd.DataFrame({
        "asset_id": dataset_df[asset_id_col].values,
        "date": dataset_df[date_col].values,
        probability_col: probabilities[:, positive_idx],
        prediction_col: predicted_class,
        "classifier_name": classifier_pack["classifier_name"],
        "positive_class": positive_class,
    })
    if label_col in dataset_df.columns:
        result[label_col] = dataset_df[label_col].values
    return result


def evaluate_classifier_predictions(
    predictions_df: pd.DataFrame,
    *,
    label_col: str,
    probability_col: str = "predicted_probability",
    prediction_col: str = "predicted_class",
) -> dict[str, Any]:
    _require_columns(predictions_df, [prediction_col, probability_col])
    if label_col not in predictions_df.columns:
        return {
            "row_count": int(len(predictions_df)),
            "error": f"label column {label_col!r} not found in predictions",
        }

    from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score

    frame = predictions_df[[label_col, prediction_col, probability_col]].copy()
    frame[label_col] = pd.to_numeric(frame[label_col], errors="coerce")
    frame[prediction_col] = pd.to_numeric(frame[prediction_col], errors="coerce")
    frame[probability_col] = pd.to_numeric(frame[probability_col], errors="coerce")
    frame = frame.dropna(subset=[label_col, prediction_col, probability_col])
    if frame.empty:
        return {"row_count": 0}

    y_true = frame[label_col].astype(int).to_numpy()
    y_pred = frame[prediction_col].astype(int).to_numpy()
    y_prob = frame[probability_col].astype(float).to_numpy()
    positive_rate = float(np.mean(y_true == 1))
    prediction_positive_rate = float(np.mean(y_pred == 1))

    metrics: dict[str, Any] = {
        "row_count": int(len(frame)),
        "positive_rate": json_safe_float(positive_rate),
        "prediction_positive_rate": json_safe_float(prediction_positive_rate),
        "accuracy": json_safe_float(accuracy_score(y_true, y_pred)),
        "precision": json_safe_float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": json_safe_float(recall_score(y_true, y_pred, zero_division=0)),
        "mean_predicted_probability": json_safe_float(np.mean(y_prob)),
    }
    if len(np.unique(y_true)) >= 2:
        metrics["roc_auc"] = json_safe_float(roc_auc_score(y_true, y_prob))
    else:
        metrics["roc_auc"] = None
    return metrics


def extract_classifier_feature_importance(
    classifier_pack: dict[str, Any],
) -> pd.DataFrame:
    model = classifier_pack["model"]
    feature_cols = classifier_pack["feature_cols"]
    classifier_name = classifier_pack["classifier_name"]
    importance_type = "none"
    values: list[float | None]
    if classifier_name == "logistic_regression_classifier" and hasattr(model, "coef_"):
        values = [float(value) for value in model.coef_[0]]
        importance_type = "coefficient"
    elif hasattr(model, "feature_importances_"):
        values = [float(value) for value in model.feature_importances_]
        importance_type = "feature_importances_"
    else:
        values = [None] * len(feature_cols)
    return pd.DataFrame({
        "feature": feature_cols,
        "importance": values,
        "importance_type": importance_type,
        "classifier_name": classifier_name,
    })


def write_classifier_artifacts(
    output_dir: Path | str,
    *,
    classifier_pack: dict[str, Any],
    predictions: pd.DataFrame,
    metrics: dict[str, Any],
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    train_config: dict[str, Any],
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    predictions_path = output_dir / "predictions.csv"
    predictions.to_csv(predictions_path, index=False)

    metrics_path = output_dir / "metrics.json"
    metrics_payload = {
        **metrics,
        "train_row_count": int(len(train_df)),
        "test_row_count": int(len(test_df)),
        "classes": classifier_pack["classes"],
        "positive_class": classifier_pack["positive_class"],
    }
    write_json_artifact(metrics_path, metrics_payload)

    feature_importance = extract_classifier_feature_importance(classifier_pack)
    feature_importance_path = output_dir / "feature_importance.csv"
    feature_importance.to_csv(feature_importance_path, index=False)

    train_config_path = output_dir / "train_config.json"
    write_json_artifact(train_config_path, train_config)

    return {
        "predictions": predictions_path,
        "metrics": metrics_path,
        "feature_importance": feature_importance_path,
        "train_config": train_config_path,
    }


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
