from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.ml_diagnostics import (
    load_predictions,
    run_ml_prediction_diagnostics,
    write_ml_prediction_diagnostics,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run diagnostics on ML prediction artifacts")
    parser.add_argument("--predictions", required=True, type=Path, help="Path to predictions.csv or .parquet")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for diagnostic artifacts")
    parser.add_argument("--prediction-col", default="predicted_return")
    parser.add_argument("--label-col", default="ret_fwd_1m")
    parser.add_argument("--asset-id-col", default="asset_id")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--quantiles", type=int, default=5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    predictions = load_predictions(args.predictions)
    result = run_ml_prediction_diagnostics(
        predictions,
        prediction_col=args.prediction_col,
        label_col=args.label_col,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        quantiles=args.quantiles,
    )
    paths = write_ml_prediction_diagnostics(result, args.output_dir)
    print(json.dumps({"status": "ok", "output_dir": str(args.output_dir), "summary": result.summary, "paths": paths}, indent=2, default=str))


if __name__ == "__main__":
    main()
