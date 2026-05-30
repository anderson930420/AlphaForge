from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.classification_labels import build_binary_return_classification_labels


def test_build_binary_return_classification_labels_maps_threshold() -> None:
    labels = pd.DataFrame({
        "asset_id": ["A", "B", "C"],
        "date": ["2024-01-31", "2024-01-31", "2024-01-31"],
        "ret_fwd_1m": [0.02, 0.0, -0.01],
    })

    result = build_binary_return_classification_labels(labels, threshold=0.0)

    assert result["ret_fwd_1m_positive"].tolist() == [1, 0, 0]
    assert set(result["classification_threshold"]) == {0.0}
    assert set(result["classification_return_col"]) == {"ret_fwd_1m"}


def test_build_binary_return_classification_labels_uses_custom_threshold_and_label_col() -> None:
    labels = pd.DataFrame({"ret_fwd_1m": [0.03, 0.01, -0.02]})

    result = build_binary_return_classification_labels(
        labels,
        label_col="top_return",
        threshold=0.02,
    )

    assert result["top_return"].tolist() == [1, 0, 0]


def test_build_binary_return_classification_labels_drops_missing_returns() -> None:
    labels = pd.DataFrame({"ret_fwd_1m": [0.02, None, -0.01]})

    result = build_binary_return_classification_labels(labels)

    assert len(result) == 2
    assert result["ret_fwd_1m_positive"].tolist() == [1, 0]


def test_build_binary_return_classification_labels_requires_return_column() -> None:
    with pytest.raises(ValueError, match="return_col 'ret_fwd_1m' not found"):
        build_binary_return_classification_labels(pd.DataFrame({"x": [1]}))
