#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.crsp_ml_e2e import run_crsp_ml_e2e_pipeline
from alphaforge.crsp_sklearn_baseline import SUPPORTED_CRSP_SKLEARN_MODELS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the CRSP ML end-to-end pipeline from raw monthly panel to sklearn baseline artifacts."
    )
    parser.add_argument("--monthly-input", required=True, type=Path, help="External CRSP monthly parquet panel")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for E2E pipeline artifacts")
    parser.add_argument("--start-date", default=None, type=str, help="Optional inclusive dataset start date")
    parser.add_argument("--end-date", default=None, type=str, help="Optional inclusive dataset end date")
    parser.add_argument("--min-mom-obs", type=int, default=8)
    parser.add_argument("--drop-missing-label", action="store_true")
    parser.add_argument("--drop-missing-features", action="store_true")
    parser.add_argument("--common-shares-only", action="store_true")
    parser.add_argument("--primary-exchange-only", action="store_true")
    parser.add_argument("--train-years", type=int, default=10)
    parser.add_argument("--test-years", type=int, default=1)
    parser.add_argument("--step-years", type=int, default=1)
    parser.add_argument(
        "--model",
        default="ridge",
        choices=SUPPORTED_CRSP_SKLEARN_MODELS,
        help="Sklearn regression model to train per walk-forward window",
    )
    parser.add_argument("--quantile", type=float, default=0.1, help="Cross-sectional long/short quantile")
    parser.add_argument("--random-state", type=int, default=0, help="Random seed for deterministic models")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = run_crsp_ml_e2e_pipeline(
        monthly_input=args.monthly_input,
        output_dir=args.output_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        min_mom_obs=args.min_mom_obs,
        drop_missing_label=args.drop_missing_label,
        drop_missing_features=args.drop_missing_features,
        common_shares_only=args.common_shares_only,
        primary_exchange_only=args.primary_exchange_only,
        train_years=args.train_years,
        test_years=args.test_years,
        step_years=args.step_years,
        model_name=args.model,
        quantile=args.quantile,
        random_state=args.random_state,
    )
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
