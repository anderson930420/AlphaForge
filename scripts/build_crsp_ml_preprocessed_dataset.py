#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.crsp_ml_preprocessing import (
    build_crsp_ml_preprocessed_dataset,
    build_crsp_ml_preprocessing_qc,
    write_feature_columns_json,
)
from alphaforge.json_utils import write_json_artifact
from alphaforge.parquet_io import read_parquet_artifact, write_parquet_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a month-by-month cross-sectional CRSP ML preprocessing dataset."
    )
    parser.add_argument("--input", required=True, type=Path, help="Input CRSP ML parquet dataset")
    parser.add_argument("--output", required=True, type=Path, help="Output parquet path for the preprocessed dataset")
    parser.add_argument("--qc-output", required=True, type=Path, help="Output JSON path for the QC summary")
    parser.add_argument(
        "--feature-columns-output",
        required=True,
        type=Path,
        help="Output JSON path for the transformed feature column manifest",
    )
    parser.add_argument(
        "--method",
        default="rank",
        choices=("rank", "zscore", "winsorized_zscore"),
        help="Cross-sectional preprocessing method",
    )
    parser.add_argument("--lower-quantile", type=float, default=0.01, help="Lower winsorization quantile")
    parser.add_argument("--upper-quantile", type=float, default=0.99, help="Upper winsorization quantile")
    parser.add_argument("--drop-missing-label", action="store_true", help="Drop rows with missing labels")
    parser.add_argument(
        "--drop-missing-features",
        action="store_true",
        help="Drop rows with any missing transformed features",
    )
    parser.add_argument(
        "--keep-original-features",
        action="store_true",
        help="Retain the original raw feature columns in the output dataset",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    qc_output_path = Path(args.qc_output)
    feature_columns_output_path = Path(args.feature_columns_output)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    qc_output_path.parent.mkdir(parents=True, exist_ok=True)
    feature_columns_output_path.parent.mkdir(parents=True, exist_ok=True)

    input_frame = read_parquet_artifact(input_path)
    processed, transformed_feature_cols = build_crsp_ml_preprocessed_dataset(
        input_frame,
        method=args.method,
        keep_original_features=bool(args.keep_original_features),
        lower_quantile=args.lower_quantile,
        upper_quantile=args.upper_quantile,
    )

    if args.drop_missing_label:
        processed = processed.dropna(subset=["forward_1m_total_ret"])
    if args.drop_missing_features:
        processed = processed.dropna(subset=transformed_feature_cols)

    processed = processed.sort_values(["date", "asset_id"], kind="mergesort").reset_index(drop=True)
    write_parquet_artifact(processed, output_path, index=False)

    qc = build_crsp_ml_preprocessing_qc(
        processed,
        transformed_feature_cols=transformed_feature_cols,
        label_col="forward_1m_total_ret",
        method=args.method,
    )
    write_json_artifact(qc_output_path, qc)
    write_feature_columns_json(feature_columns_output_path, transformed_feature_cols)

    print(json.dumps(qc, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
