from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alphaforge.crsp_ml_preprocessing import (
    DEFAULT_CRSP_ML_FEATURE_COLUMNS,
    build_crsp_ml_preprocessed_dataset,
    build_crsp_ml_preprocessing_qc,
    cross_sectional_rank_features,
    cross_sectional_zscore_features,
    validate_preprocessing_frame,
    write_feature_columns_json,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_crsp_ml_preprocessed_dataset.py"


def _make_preprocessing_frame() -> pd.DataFrame:
    rows = [
        {
            "date": "2021-02-28",
            "asset_id": "B",
            "permno": 1002,
            "ticker": "BBB",
            "mom12_1": 20.0,
            "mom6_1": 30.0,
            "mom3_1": 40.0,
            "ret1_0": 0.4,
            "volatility_12m": 2.0,
            "turnover": 1.6,
            "log_market_cap": 7.3,
            "log_price": 2.3,
            "forward_1m_total_ret": 0.04,
        },
        {
            "date": "2021-01-31",
            "asset_id": "B",
            "permno": 1002,
            "ticker": "BBB",
            "mom12_1": 2.0,
            "mom6_1": 3.0,
            "mom3_1": 4.0,
            "ret1_0": 0.2,
            "volatility_12m": 1.0,
            "turnover": np.nan,
            "log_market_cap": 7.1,
            "log_price": 2.1,
            "forward_1m_total_ret": np.nan,
        },
        {
            "date": "2021-01-31",
            "asset_id": "A",
            "permno": 1001,
            "ticker": "AAA",
            "mom12_1": 1.0,
            "mom6_1": 2.0,
            "mom3_1": 3.0,
            "ret1_0": 0.1,
            "volatility_12m": 1.0,
            "turnover": 1.0,
            "log_market_cap": 7.0,
            "log_price": 2.0,
            "forward_1m_total_ret": 0.01,
        },
        {
            "date": "2021-02-28",
            "asset_id": "A",
            "permno": 1001,
            "ticker": "AAA",
            "mom12_1": 10.0,
            "mom6_1": 20.0,
            "mom3_1": 30.0,
            "ret1_0": 0.3,
            "volatility_12m": 2.0,
            "turnover": 1.5,
            "log_market_cap": 7.2,
            "log_price": 2.2,
            "forward_1m_total_ret": 0.03,
        },
    ]
    return pd.DataFrame(rows)


def _make_single_feature_frame(values_by_date: dict[str, list[float | None]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for date_value, values in values_by_date.items():
        for index, value in enumerate(values):
            rows.append(
                {
                    "date": date_value,
                    "asset_id": chr(ord("A") + index),
                    "signal": value,
                    "forward_1m_total_ret": float(index + 1) / 100.0,
                }
            )
    return pd.DataFrame(rows)


def _series_by_month_asset(
    df: pd.DataFrame,
    *,
    date: str,
    column: str,
) -> pd.Series:
    return (
        df.loc[df["date"] == pd.Timestamp(date)]
        .sort_values("asset_id")
        .set_index("asset_id")[column]
    )


def test_validate_preprocessing_frame_rejects_missing_feature_columns() -> None:
    frame = _make_preprocessing_frame().drop(columns=["mom3_1"])

    with pytest.raises(ValueError, match="Missing required preprocessing columns"):
        validate_preprocessing_frame(frame, feature_cols=list(DEFAULT_CRSP_ML_FEATURE_COLUMNS))


def test_validate_preprocessing_frame_rejects_duplicate_asset_date_rows() -> None:
    frame = _make_preprocessing_frame()
    duplicated = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate asset_id/date rows are not allowed"):
        validate_preprocessing_frame(duplicated, feature_cols=list(DEFAULT_CRSP_ML_FEATURE_COLUMNS))


def test_cross_sectional_rank_features_are_month_specific_and_shifted() -> None:
    frame = _make_single_feature_frame(
        {
            "2021-01-31": [1.0, 2.0, 3.0],
            "2021-02-28": [10.0, 20.0, 30.0],
        }
    )

    ranked = cross_sectional_rank_features(frame, feature_cols=["signal"])
    jan = ranked.loc[ranked["date"] == pd.Timestamp("2021-01-31")].set_index("asset_id")["signal_xrank"]
    feb = ranked.loc[ranked["date"] == pd.Timestamp("2021-02-28")].set_index("asset_id")["signal_xrank"]

    expected = [-1.0 / 6.0, 1.0 / 6.0, 0.5]
    assert jan.tolist() == pytest.approx(expected)
    assert feb.tolist() == pytest.approx(expected)
    assert jan.tolist() == pytest.approx(feb.tolist())


def test_rank_preprocessing_does_not_leak_across_months_when_future_order_changes() -> None:
    base = _make_single_feature_frame(
        {
            "2021-01-31": [1.0, 2.0, 3.0],
            "2021-02-28": [10.0, 20.0, 30.0],
        }
    )
    perturbed = base.copy()
    perturbed.loc[
        (perturbed["date"] == "2021-02-28") & (perturbed["asset_id"] == "A"),
        "signal",
    ] = 40.0

    base_processed, _ = build_crsp_ml_preprocessed_dataset(
        base,
        feature_cols=["signal"],
        method="rank",
    )
    perturbed_processed, _ = build_crsp_ml_preprocessed_dataset(
        perturbed,
        feature_cols=["signal"],
        method="rank",
    )

    base_jan = _series_by_month_asset(base_processed, date="2021-01-31", column="signal_xrank")
    perturbed_jan = _series_by_month_asset(perturbed_processed, date="2021-01-31", column="signal_xrank")
    base_feb = _series_by_month_asset(base_processed, date="2021-02-28", column="signal_xrank")
    perturbed_feb = _series_by_month_asset(perturbed_processed, date="2021-02-28", column="signal_xrank")

    pd.testing.assert_series_equal(base_jan, perturbed_jan)
    assert not base_feb.equals(perturbed_feb)


def test_cross_sectional_zscore_features_are_month_specific() -> None:
    frame = _make_single_feature_frame(
        {
            "2021-01-31": [1.0, 2.0, 3.0],
            "2021-02-28": [100.0, 200.0, 300.0],
        }
    )

    zscored = cross_sectional_zscore_features(frame, feature_cols=["signal"])
    jan = zscored.loc[zscored["date"] == pd.Timestamp("2021-01-31")].set_index("asset_id")["signal_xz"]
    feb = zscored.loc[zscored["date"] == pd.Timestamp("2021-02-28")].set_index("asset_id")["signal_xz"]

    expected = [-1.0, 0.0, 1.0]
    assert jan.tolist() == pytest.approx(expected)
    assert feb.tolist() == pytest.approx(expected)
    assert jan.tolist() == pytest.approx(feb.tolist())


@pytest.mark.parametrize(
    ("method", "column"),
    [
        ("zscore", "signal_xz"),
        ("winsorized_zscore", "signal_xwz"),
    ],
)
def test_zscore_preprocessing_does_not_leak_across_months_when_future_value_changes(
    method: str,
    column: str,
) -> None:
    base = _make_single_feature_frame(
        {
            "2021-01-31": [1.0, 2.0, 3.0],
            "2021-02-28": [10.0, 20.0, 30.0],
        }
    )
    perturbed = base.copy()
    perturbed.loc[
        (perturbed["date"] == "2021-02-28") & (perturbed["asset_id"] == "C"),
        "signal",
    ] = 999999999.0

    base_processed, _ = build_crsp_ml_preprocessed_dataset(
        base,
        feature_cols=["signal"],
        method=method,
    )
    perturbed_processed, _ = build_crsp_ml_preprocessed_dataset(
        perturbed,
        feature_cols=["signal"],
        method=method,
    )

    base_jan = _series_by_month_asset(base_processed, date="2021-01-31", column=column)
    perturbed_jan = _series_by_month_asset(perturbed_processed, date="2021-01-31", column=column)
    base_feb = _series_by_month_asset(base_processed, date="2021-02-28", column=column)
    perturbed_feb = _series_by_month_asset(perturbed_processed, date="2021-02-28", column=column)

    pd.testing.assert_series_equal(base_jan, perturbed_jan)
    assert not base_feb.equals(perturbed_feb)


def test_winsorized_zscore_caps_outliers_before_scaling() -> None:
    frame = _make_single_feature_frame({"2021-01-31": [1.0, 2.0, 100.0]})

    zscored = cross_sectional_zscore_features(
        frame,
        feature_cols=["signal"],
        winsorize=True,
        lower_quantile=0.0,
        upper_quantile=0.5,
    )
    values = zscored.set_index("asset_id")["signal_xz"]

    expected = [-1.1547005383792517, 0.5773502691896258, 0.5773502691896258]
    assert values.tolist() == pytest.approx(expected)
    assert values.loc["B"] == pytest.approx(values.loc["C"])


def test_missing_inputs_remain_missing() -> None:
    frame = _make_single_feature_frame({"2021-01-31": [1.0, None, 3.0]})

    ranked = cross_sectional_rank_features(frame, feature_cols=["signal"])
    zscored = cross_sectional_zscore_features(frame, feature_cols=["signal"])

    assert pd.isna(ranked.loc[ranked["asset_id"] == "B", "signal_xrank"].iloc[0])
    assert pd.isna(zscored.loc[zscored["asset_id"] == "B", "signal_xz"].iloc[0])


def test_zero_variance_cross_section_outputs_zero_for_non_missing_values() -> None:
    frame = _make_single_feature_frame({"2021-01-31": [5.0, 5.0, 5.0]})

    zscored = cross_sectional_zscore_features(frame, feature_cols=["signal"])
    values = zscored["signal_xz"].tolist()

    assert values == pytest.approx([0.0, 0.0, 0.0])


def test_build_crsp_ml_preprocessed_dataset_preserves_label_and_returns_transformed_columns() -> None:
    frame = _make_preprocessing_frame()

    processed, transformed_cols = build_crsp_ml_preprocessed_dataset(
        frame,
        method="rank",
        keep_original_features=True,
    )
    processed_without_raw, _ = build_crsp_ml_preprocessed_dataset(
        frame,
        method="rank",
        keep_original_features=False,
    )

    expected_labels = frame.sort_values(["date", "asset_id"], kind="mergesort")["forward_1m_total_ret"].reset_index(
        drop=True
    )

    assert transformed_cols == [f"{column}_xrank" for column in DEFAULT_CRSP_ML_FEATURE_COLUMNS]
    assert all(column in processed.columns for column in DEFAULT_CRSP_ML_FEATURE_COLUMNS)
    assert all(column in processed.columns for column in transformed_cols)
    assert all(column not in processed_without_raw.columns for column in DEFAULT_CRSP_ML_FEATURE_COLUMNS)
    pd.testing.assert_series_equal(
        processed["forward_1m_total_ret"].reset_index(drop=True),
        expected_labels,
        check_names=False,
    )


def test_build_crsp_ml_preprocessing_qc_reports_expected_counts_and_missing_ratios() -> None:
    frame = _make_preprocessing_frame()
    processed, transformed_cols = build_crsp_ml_preprocessed_dataset(frame, method="rank")

    qc = build_crsp_ml_preprocessing_qc(
        processed,
        transformed_feature_cols=transformed_cols,
        label_col="forward_1m_total_ret",
        method="rank",
    )

    assert qc["rows"] == 4
    assert qc["assets"] == 2
    assert qc["date_min"] == "2021-01-31"
    assert qc["date_max"] == "2021-02-28"
    assert qc["months"] == 2
    assert qc["method"] == "rank"
    assert qc["transformed_feature_columns"] == transformed_cols
    assert qc["label_column"] == "forward_1m_total_ret"
    assert qc["duplicate_asset_date_rows"] == 0
    assert qc["missing_label_ratio"] == pytest.approx(0.25)
    assert qc["missing_turnover_xrank_ratio"] == pytest.approx(0.25)
    assert qc["frequency"] == "monthly"


def test_write_feature_columns_json_writes_expected_schema(tmp_path: Path) -> None:
    output_path = tmp_path / "feature_columns.json"

    write_feature_columns_json(
        output_path,
        ["mom12_1_xrank", "mom6_1_xrank"],
        raw_feature_cols=["mom12_1", "mom6_1"],
        method="rank",
        label_col="forward_1m_total_ret",
        keep_original_features=True,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {
        "feature_columns": ["mom12_1_xrank", "mom6_1_xrank"],
        "count": 2,
        "raw_feature_columns": ["mom12_1", "mom6_1"],
        "method": "rank",
        "label_column": "forward_1m_total_ret",
        "date_column": "date",
        "asset_column": "asset_id",
        "keep_original_features": True,
        "lower_quantile": None,
        "upper_quantile": None,
    }


def test_preprocessing_cli_writes_dataset_qc_and_feature_columns_json(tmp_path: Path) -> None:
    input_path = tmp_path / "input.parquet"
    output_path = tmp_path / "output.parquet"
    qc_output_path = tmp_path / "qc.json"
    feature_columns_output_path = tmp_path / "feature_columns.json"

    frame = _make_preprocessing_frame()
    frame.to_parquet(input_path, index=False)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--qc-output",
            str(qc_output_path),
            "--feature-columns-output",
            str(feature_columns_output_path),
            "--method",
            "rank",
            "--drop-missing-label",
            "--keep-original-features",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    assert qc_output_path.exists()
    assert feature_columns_output_path.exists()

    stdout_qc = json.loads(result.stdout)
    file_qc = json.loads(qc_output_path.read_text(encoding="utf-8"))
    feature_columns_payload = json.loads(feature_columns_output_path.read_text(encoding="utf-8"))
    output_frame = pd.read_parquet(output_path)

    assert stdout_qc == file_qc
    assert file_qc["rows"] == 3
    assert file_qc["assets"] == 2
    assert file_qc["months"] == 2
    assert file_qc["missing_label_ratio"] == 0.0
    assert feature_columns_payload == {
        "feature_columns": [f"{column}_xrank" for column in DEFAULT_CRSP_ML_FEATURE_COLUMNS],
        "count": 8,
        "raw_feature_columns": list(DEFAULT_CRSP_ML_FEATURE_COLUMNS),
        "method": "rank",
        "label_column": "forward_1m_total_ret",
        "date_column": "date",
        "asset_column": "asset_id",
        "keep_original_features": True,
        "lower_quantile": None,
        "upper_quantile": None,
    }
    assert {"mom12_1", "mom12_1_xrank", "forward_1m_total_ret"}.issubset(set(output_frame.columns))
    assert not output_frame["forward_1m_total_ret"].isna().any()
    assert len(output_frame) == 3
