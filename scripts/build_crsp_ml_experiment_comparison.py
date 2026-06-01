#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.crsp_ml_experiment_comparison import (
    parse_experiment_arg,
    write_crsp_ml_experiment_comparison,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a CRSP ML experiment comparison report from existing artifacts."
    )
    parser.add_argument(
        "--experiment",
        action="append",
        required=True,
        help="Repeatable NAME=DIR experiment artifact directory, usually containing summary.json",
    )
    parser.add_argument(
        "--mom12m-dir",
        default=None,
        type=Path,
        help="Optional directory containing momentum_summary.json",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory for comparison.json and comparison.md",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        experiment_specs = [parse_experiment_arg(item) for item in args.experiment]
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    comparison = write_crsp_ml_experiment_comparison(
        experiment_specs,
        mom12m_dir=args.mom12m_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps(comparison, indent=2, default=str))


if __name__ == "__main__":
    main()
