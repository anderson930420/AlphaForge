#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from alphaforge.crsp_ml_dataset import build_crsp_ml_dataset, build_crsp_ml_dataset_qc
from alphaforge.crsp_monthly_panel import load_crsp_monthly_panel
from alphaforge.json_utils import write_json_artifact


_LOADER_COLUMNS = [
    "date",
    "asset_id",
    "permno",
    "ticker",
    "total_ret",
    "ret",
    "retx",
    "dlret",
    "price",
    "volume",
    "shares_out",
    "market_cap",
    "lag_market_cap",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build an ML-ready CRSP monthly dataset from an external canonical panel"
    )
    parser.add_argument("--input", required=True, type=Path, help="External CRSP monthly parquet panel")
    parser.add_argument("--output", required=True, type=Path, help="Output parquet path for the dataset")
    parser.add_argument("--qc-output", required=True, type=Path, help="Output JSON path for QC summary")
    parser.add_argument("--start-date", default=None, type=str, help="Optional dataset start date")
    parser.add_argument("--end-date", default=None, type=str, help="Optional dataset end date")
    parser.add_argument("--min-mom-obs", type=int, default=8)
    parser.add_argument("--drop-missing-label", action="store_true")
    parser.add_argument("--drop-missing-features", action="store_true")
    parser.add_argument("--common-shares-only", action="store_true")
    parser.add_argument("--primary-exchange-only", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    qc_output_path = Path(args.qc_output)
    qc_output_path.parent.mkdir(parents=True, exist_ok=True)

    start_date = _parse_optional_date(args.start_date, field_name="start_date")
    end_date = _parse_optional_date(args.end_date, field_name="end_date")
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date must be on or before end_date")

    panel = load_crsp_monthly_panel(
        args.input,
        common_shares_only=args.common_shares_only,
        primary_exchange_only=args.primary_exchange_only,
        columns=_LOADER_COLUMNS,
    )

    dataset = build_crsp_ml_dataset(
        panel,
        min_mom_obs=args.min_mom_obs,
        drop_missing_label=args.drop_missing_label,
        drop_missing_features=args.drop_missing_features,
    )
    dataset = _filter_dataset_window(dataset, start_date=start_date, end_date=end_date)

    dataset.to_parquet(output_path, index=False)

    qc = build_crsp_ml_dataset_qc(dataset)
    qc.update(
        {
            "status": "ok",
            "input": str(args.input),
            "output": str(output_path),
            "qc_output": str(qc_output_path),
            "start_date": args.start_date,
            "end_date": args.end_date,
            "min_mom_obs": int(args.min_mom_obs),
            "drop_missing_label": bool(args.drop_missing_label),
            "drop_missing_features": bool(args.drop_missing_features),
            "common_shares_only": bool(args.common_shares_only),
            "primary_exchange_only": bool(args.primary_exchange_only),
        }
    )

    write_json_artifact(qc_output_path, qc)
    print(json.dumps(qc, indent=2, sort_keys=True, default=str))


def _filter_dataset_window(
    dataset: pd.DataFrame,
    *,
    start_date: pd.Timestamp | None,
    end_date: pd.Timestamp | None,
) -> pd.DataFrame:
    frame = dataset.copy()
    if frame.empty:
        return frame

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if frame["date"].isna().any():
        invalid_values = frame.loc[frame["date"].isna(), "date"].astype(str).head(5).tolist()
        raise ValueError(f"date must be parseable as datetime; invalid values: {invalid_values}")

    if start_date is not None:
        frame = frame.loc[frame["date"] >= start_date]
    if end_date is not None:
        frame = frame.loc[frame["date"] <= end_date]
    return frame.reset_index(drop=True)


def _parse_optional_date(value: str | None, *, field_name: str) -> pd.Timestamp | None:
    if value is None:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"{field_name} must be parseable as datetime: {value!r}")
    return pd.Timestamp(parsed) + pd.offsets.MonthEnd(0)


if __name__ == "__main__":
    main()
