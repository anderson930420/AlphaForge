from __future__ import annotations

import pandas as pd


DEFAULT_CLASSIFICATION_LABEL_COL = "ret_fwd_1m_positive"


def build_binary_return_classification_labels(
    labels_df: pd.DataFrame,
    *,
    return_col: str = "ret_fwd_1m",
    label_col: str = DEFAULT_CLASSIFICATION_LABEL_COL,
    threshold: float = 0.0,
    positive_label: int = 1,
    negative_label: int = 0,
    drop_missing_return: bool = True,
) -> pd.DataFrame:
    """Build a binary classification target from an existing forward-return label.

    Rows with ``return_col > threshold`` receive ``positive_label``. Rows with
    ``return_col <= threshold`` receive ``negative_label``. Missing returns are
    dropped by default so classifier training does not silently learn an
    arbitrary class for unavailable targets.
    """
    if labels_df.empty:
        raise ValueError("Empty label panel")
    if return_col not in labels_df.columns:
        raise ValueError(f"return_col {return_col!r} not found in labels")
    if positive_label == negative_label:
        raise ValueError("positive_label and negative_label must differ")

    frame = labels_df.copy()
    returns = pd.to_numeric(frame[return_col], errors="coerce")
    if drop_missing_return:
        frame = frame.loc[returns.notna()].copy()
        returns = returns.loc[frame.index]
    if frame.empty:
        raise ValueError("No valid return rows after classification label filtering")

    frame[label_col] = negative_label
    frame.loc[returns > float(threshold), label_col] = positive_label
    frame[label_col] = frame[label_col].astype(int)
    frame["classification_threshold"] = float(threshold)
    frame["classification_return_col"] = return_col
    return frame.reset_index(drop=True)
