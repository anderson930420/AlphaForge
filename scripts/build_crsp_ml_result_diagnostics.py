#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.crsp_ml_result_diagnostics import write_crsp_ml_result_diagnostics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build diagnostics and comparison artifacts from existing CRSP ML results."
    )
    parser.add_argument(
        "--ml-e2e-dir",
        required=True,
        type=Path,
        help="Directory containing CRSP ML E2E artifacts",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory for diagnostics artifacts",
    )
    parser.add_argument(
        "--mom12m-dir",
        default=None,
        type=Path,
        help="Optional directory containing Mom12m baseline artifacts",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    diagnostics = write_crsp_ml_result_diagnostics(
        ml_e2e_dir=args.ml_e2e_dir,
        output_dir=args.output_dir,
        mom12m_dir=args.mom12m_dir,
    )
    print(json.dumps(diagnostics, indent=2, default=str))


if __name__ == "__main__":
    main()
