from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.ml_demo_artifacts import write_synthetic_prediction_demo_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate synthetic ML prediction demo artifacts")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--assets", type=int, default=20)
    parser.add_argument("--quantiles", type=int, default=5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = write_synthetic_prediction_demo_artifacts(
        args.output_dir,
        months=args.months,
        assets=args.assets,
        quantiles=args.quantiles,
    )
    print(json.dumps({"status": "ok", "output_dir": str(args.output_dir), "paths": paths}, indent=2, default=str))


if __name__ == "__main__":
    main()
