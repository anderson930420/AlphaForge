from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.ml_classifiers import (
    evaluate_classifier_predictions,
    fit_sklearn_classifier,
    predict_sklearn_classifier,
)
from alphaforge.ml_models import _require_sklearn


def _require_sklearn_test() -> bool:
    try:
        _require_sklearn()
        return True
    except ImportError:
        return False


SKLEARN_AVAILABLE = _require_sklearn_test()


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_fit_predict_evaluate_logistic_classifier() -> None:
    train = pd.DataFrame({
        "asset_id": ["A", "B", "C", "D"],
        "date": pd.to_datetime(["2024-01-31", "2024-01-31", "2024-02-29", "2024-02-29"]),
        "x1": [1.0, -1.0, 1.5, -1.5],
        "x2": [0.2, -0.2, 0.3, -0.3],
        "target": [1, 0, 1, 0],
    })
    test = pd.DataFrame({
        "asset_id": ["E", "F"],
        "date": pd.to_datetime(["2024-03-31", "2024-03-31"]),
        "x1": [2.0, -2.0],
        "x2": [0.4, -0.4],
        "target": [1, 0],
    })

    pack = fit_sklearn_classifier(
        train,
        classifier_name="logistic_regression_classifier",
        feature_cols=["x1", "x2"],
        label_col="target",
        random_state=1,
    )
    predictions = predict_sklearn_classifier(pack, test)
    metrics = evaluate_classifier_predictions(predictions, label_col="target")

    assert set(predictions.columns) >= {"predicted_probability", "predicted_class", "target"}
    assert predictions["predicted_probability"].between(0.0, 1.0).all()
    assert metrics["row_count"] == 2
    assert metrics["accuracy"] is not None
    assert "roc_auc" in metrics


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_fit_classifier_requires_two_classes() -> None:
    train = pd.DataFrame({
        "x1": [1.0, 2.0, 3.0],
        "target": [1, 1, 1],
    })

    with pytest.raises(ValueError, match="at least two classes"):
        fit_sklearn_classifier(
            train,
            classifier_name="logistic_regression_classifier",
            feature_cols=["x1"],
            label_col="target",
        )


def test_evaluate_classifier_predictions_without_label_returns_error() -> None:
    predictions = pd.DataFrame({
        "predicted_probability": [0.2, 0.8],
        "predicted_class": [0, 1],
    })

    metrics = evaluate_classifier_predictions(predictions, label_col="target")

    assert metrics["row_count"] == 2
    assert "label column 'target' not found" in metrics["error"]
