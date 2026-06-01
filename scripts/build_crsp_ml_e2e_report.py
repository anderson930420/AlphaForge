#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.crsp_ml_e2e_report import write_crsp_ml_e2e_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a human-readable report from existing CRSP ML E2E artifacts."
    )
    parser.add_argument("--e2e-dir", required=True, type=Path, help="Directory containing CRSP ML E2E artifacts")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for report artifacts")
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Skip writing report.html and only write report.json/report.md",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = write_crsp_ml_e2e_report(
        args.e2e_dir,
        args.output_dir,
        write_html=not args.no_html,
    )
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
