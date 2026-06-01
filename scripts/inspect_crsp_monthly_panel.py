#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.crsp_monthly_panel import build_crsp_monthly_panel_qc, load_crsp_monthly_panel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect an external CRSP monthly parquet panel")
    parser.add_argument("--input", required=True, type=Path, help="Path to the external monthly parquet panel")
    parser.add_argument("--start-date", default=None, help="Optional inclusive start date filter")
    parser.add_argument("--end-date", default=None, help="Optional inclusive end date filter")
    parser.add_argument("--common-shares-only", action="store_true", help="Filter to common shares only")
    parser.add_argument(
        "--primary-exchange-only",
        action="store_true",
        help="Filter to primary US exchanges only",
    )
    parser.add_argument("--qc-output", default=None, type=Path, help="Optional path for QC JSON output")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    frame = load_crsp_monthly_panel(
        args.input,
        start_date=args.start_date,
        end_date=args.end_date,
        common_shares_only=args.common_shares_only,
        primary_exchange_only=args.primary_exchange_only,
    )
    qc = build_crsp_monthly_panel_qc(frame)
    payload = json.dumps(qc, indent=2, sort_keys=True)
    print(payload)

    if args.qc_output is not None:
        args.qc_output.parent.mkdir(parents=True, exist_ok=True)
        args.qc_output.write_text(payload + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
