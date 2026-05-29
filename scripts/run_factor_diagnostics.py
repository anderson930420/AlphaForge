from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.factor_diagnostics import (
    load_supervised_panel,
    run_factor_diagnostics,
    write_factor_diagnostics,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run single-factor diagnostics on a supervised panel")
    parser.add_argument("--panel", required=True, type=Path, help="Path to supervised_panel.csv or .parquet")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for diagnostic artifacts")
    parser.add_argument("--factor-col", required=True, help="Factor column to diagnose, e.g. Mom12m")
    parser.add_argument("--label-col", default="ret_fwd_1m")
    parser.add_argument("--asset-id-col", default="asset_id")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--quantiles", type=int, default=5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    panel = load_supervised_panel(args.panel)
    result = run_factor_diagnostics(
        panel,
        factor_col=args.factor_col,
        label_col=args.label_col,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        quantiles=args.quantiles,
    )
    paths = write_factor_diagnostics(result, args.output_dir)
    print(json.dumps({"status": "ok", "output_dir": str(args.output_dir), "summary": result.summary, "paths": paths}, indent=2, default=str))


if __name__ == "__main__":
    main()
