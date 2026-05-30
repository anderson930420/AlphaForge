from __future__ import annotations

import math

import pandas as pd
import pytest

from alphaforge.ml_models import evaluate_sklearn_predictions
from alphaforge.ml_torch import evaluate_torch_predictions
from scripts.run_sklearn_ml_model import parse_feature_cols as parse_sklearn_feature_cols
from scripts.run_torch_mlp_baseline import parse_feature_cols as parse_torch_feature_cols


def test_sklearn_evaluate_predictions_requires_prediction_column() -> None:
    predictions = pd.DataFrame({"ret_fwd_1m": [0.01, 0.02]})

    with pytest.raises(ValueError, match="Missing required columns"):
        evaluate_sklearn_predictions(predictions)


def test_torch_evaluate_predictions_requires_prediction_column() -> None:
    predictions = pd.DataFrame({"ret_fwd_1m": [0.01, 0.02]})

    with pytest.raises(ValueError, match="Missing required columns"):
        evaluate_torch_predictions(predictions)


def test_sklearn_evaluate_predictions_returns_none_for_non_finite_means() -> None:
    predictions = pd.DataFrame({
        "predicted_return": [math.nan, math.nan],
        "ret_fwd_1m": [math.nan, math.nan],
    })

    metrics = evaluate_sklearn_predictions(predictions)

    assert metrics["row_count"] == 0
    assert metrics["mean_prediction"] is None
    assert metrics["mean_label"] is None


def test_torch_evaluate_predictions_returns_none_for_non_finite_means() -> None:
    predictions = pd.DataFrame({
        "predicted_return": [math.nan, math.nan],
        "ret_fwd_1m": [math.nan, math.nan],
    })

    metrics = evaluate_torch_predictions(predictions)

    assert metrics["row_count"] == 0
    assert metrics["mean_prediction"] is None
    assert metrics["mean_label"] is None


def test_sklearn_cli_feature_cols_parser_filters_empty_items() -> None:
    assert parse_sklearn_feature_cols("Mom12m, BM,") == ["Mom12m", "BM"]


def test_torch_cli_feature_cols_parser_filters_empty_items() -> None:
    assert parse_torch_feature_cols("Mom12m, BM,") == ["Mom12m", "BM"]


def test_sklearn_cli_feature_cols_parser_rejects_empty_parsed_list() -> None:
    with pytest.raises(ValueError, match="no valid feature columns"):
        parse_sklearn_feature_cols(" , , ")


def test_torch_cli_feature_cols_parser_rejects_empty_parsed_list() -> None:
    with pytest.raises(ValueError, match="no valid feature columns"):
        parse_torch_feature_cols(" , , ")


def test_cli_feature_cols_parser_allows_omitted_value() -> None:
    assert parse_sklearn_feature_cols(None) is None
    assert parse_torch_feature_cols(None) is None
