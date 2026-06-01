#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.crsp_ml_walkforward import build_walk_forward_qc, build_walk_forward_splits
from alphaforge.json_utils import write_json_artifact
from alphaforge.parquet_io import read_parquet_artifact, write_parquet_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build deterministic walk-forward train/test splits from a CRSP ML dataset"
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to an existing CRSP ML dataset parquet")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for split parquet artifacts")
    parser.add_argument("--start-date", default=None, type=str, help="Optional inclusive dataset start date")
    parser.add_argument("--end-date", default=None, type=str, help="Optional inclusive dataset end date")
    parser.add_argument("--train-years", type=int, default=10)
    parser.add_argument("--test-years", type=int, default=1)
    parser.add_argument("--step-years", type=int, default=1)
    parser.add_argument("--qc-output", default=None, type=Path, help="Optional JSON QC output path")
    parser.add_argument("--manifest-output", default=None, type=Path, help="Optional JSON manifest output path")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = read_parquet_artifact(args.input)
    splits = build_walk_forward_splits(
        dataset,
        train_years=args.train_years,
        test_years=args.test_years,
        step_years=args.step_years,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    manifest_windows: list[dict[str, object]] = []
    for window, train_df, test_df in splits:
        window_dir = output_dir / window.window_id
        window_dir.mkdir(parents=True, exist_ok=True)
        train_path = window_dir / "train.parquet"
        test_path = window_dir / "test.parquet"

        write_parquet_artifact(train_df, train_path, index=False)
        write_parquet_artifact(test_df, test_path, index=False)

        manifest_windows.append(
            {
                "window_id": window.window_id,
                "window_dir": str(window_dir),
                "train_parquet": str(train_path),
                "test_parquet": str(test_path),
                "train_rows": int(len(train_df)),
                "test_rows": int(len(test_df)),
            }
        )

    qc = build_walk_forward_qc(splits)
    qc.update(
        {
            "status": "ok",
            "input": str(args.input),
            "output_dir": str(output_dir),
            "start_date": args.start_date,
            "end_date": args.end_date,
            "train_years_arg": int(args.train_years),
            "test_years_arg": int(args.test_years),
            "step_years_arg": int(args.step_years),
        }
    )

    payload = json.dumps(qc, indent=2, sort_keys=True, default=str)
    print(payload)

    if args.qc_output is not None:
        args.qc_output.parent.mkdir(parents=True, exist_ok=True)
        write_json_artifact(args.qc_output, qc)

    if args.manifest_output is not None:
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "status": "ok",
            "input": str(args.input),
            "output_dir": str(output_dir),
            "start_date": args.start_date,
            "end_date": args.end_date,
            "train_years": int(args.train_years),
            "test_years": int(args.test_years),
            "step_years": int(args.step_years),
            "window_count": int(len(splits)),
            "windows": manifest_windows,
        }
        write_json_artifact(args.manifest_output, manifest)


if __name__ == "__main__":
    main()
