#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.json_utils import write_json_artifact
from alphaforge.ml_signal import build_single_asset_threshold_signal, load_prediction_panel


SUMMARY_FILENAME = "single_asset_ml_signal_summary.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a one-symbol threshold-based custom_signal from single-asset ML predictions."
    )
    parser.add_argument("--predictions", required=True, type=Path, help="Prediction panel CSV or parquet")
    parser.add_argument("--output", required=True, type=Path, help="Output custom_signal CSV")
    parser.add_argument("--summary-output", type=Path, default=None, help="Optional JSON summary path")
    parser.add_argument("--asset-id", default=None, help="Asset id to select when the prediction panel has multiple assets")
    parser.add_argument("--symbol", default=None, help="Output symbol. Defaults to symbol column or asset_id")
    parser.add_argument("--asset-id-col", default="asset_id")
    parser.add_argument("--symbol-col", default=None)
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--prediction-col", default="predicted_return")
    parser.add_argument("--available-at-col", default=None)
    parser.add_argument("--signal-name", default="ml_threshold_return")
    parser.add_argument("--source", default="AlphaForgeML")
    parser.add_argument("--long-threshold", type=float, default=0.0)
    parser.add_argument("--short-threshold", type=float, default=0.0)
    parser.add_argument("--long-target-weight", type=float, default=1.0)
    parser.add_argument("--short-target-weight", type=float, default=-1.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    predictions = load_prediction_panel(args.predictions)
    signal = build_single_asset_threshold_signal(
        predictions,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        prediction_col=args.prediction_col,
        asset_id=args.asset_id,
        symbol_col=args.symbol_col,
        symbol=args.symbol,
        signal_name=args.signal_name,
        source=args.source,
        long_threshold=args.long_threshold,
        short_threshold=args.short_threshold,
        long_target_weight=args.long_target_weight,
        short_target_weight=args.short_target_weight,
        available_at_col=args.available_at_col,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    signal.to_csv(output_path, index=False)

    nonzero_count = int((signal["target_weight"].astype(float).abs() > 0.0).sum())
    summary = {
        "status": "ok",
        "stage": "single_asset_ml_threshold_signal",
        "predictions_path": str(args.predictions),
        "signal_path": str(output_path),
        "asset_id": str(signal["asset_id"].iloc[0]),
        "symbol": str(signal["symbol"].iloc[0]),
        "signal_name": args.signal_name,
        "source": args.source,
        "prediction_row_count": int(len(predictions)),
        "signal_row_count": int(len(signal)),
        "nonzero_target_weight_count": nonzero_count,
        "all_flat_signal": nonzero_count == 0,
        "long_threshold": args.long_threshold,
        "short_threshold": args.short_threshold,
        "long_target_weight": args.long_target_weight,
        "short_target_weight": args.short_target_weight,
        "does_train_model": False,
        "does_generate_predictions": False,
        "does_run_research_validation": False,
        "does_execute_live_trades": False,
        "boundary": (
            "Converts existing single-asset predictions into a one-symbol threshold-based custom_signal. "
            "It does not train models, generate predictions, or run research validation."
        ),
    }
    summary_path = args.summary_output or (output_path.parent / SUMMARY_FILENAME)
    write_json_artifact(summary_path, summary)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
