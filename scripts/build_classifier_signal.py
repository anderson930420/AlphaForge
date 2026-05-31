#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.ml_signal import build_classifier_probability_signal, load_prediction_panel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert classifier probability predictions into AlphaForge v0.2 custom_signal files."
    )
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--asset-id-col", default="asset_id")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--probability-col", default="predicted_probability")
    parser.add_argument("--symbol-col", default=None)
    parser.add_argument("--available-at-col", default=None)
    parser.add_argument("--signal-name", default="ml_predicted_probability")
    parser.add_argument("--source", default="AlphaForgeMLClassifier")
    parser.add_argument("--long-probability-threshold", type=float, default=0.6)
    parser.add_argument("--short-probability-threshold", type=float, default=0.4)
    parser.add_argument("--gross-long-weight", type=float, default=1.0)
    parser.add_argument("--gross-short-weight", type=float, default=-1.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    predictions_df = load_prediction_panel(args.predictions)
    signal = build_classifier_probability_signal(
        predictions_df,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        probability_col=args.probability_col,
        symbol_col=args.symbol_col,
        signal_name=args.signal_name,
        source=args.source,
        long_probability_threshold=args.long_probability_threshold,
        short_probability_threshold=args.short_probability_threshold,
        gross_long_weight=args.gross_long_weight,
        gross_short_weight=args.gross_short_weight,
        available_at_col=args.available_at_col,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    suffix = args.output.suffix.lower()
    if suffix == ".parquet":
        signal.to_parquet(args.output, index=False)
    else:
        signal.to_csv(args.output, index=False)

    summary = {
        "status": "ok",
        "stage": "classifier_probability_signal",
        "predictions": str(args.predictions),
        "output": str(args.output),
        "rows": int(len(signal)),
        "nonzero_target_weight_count": int((signal["target_weight"].abs() > 0).sum()),
        "long_probability_threshold": args.long_probability_threshold,
        "short_probability_threshold": args.short_probability_threshold,
        "signal_name": args.signal_name,
        "source": args.source,
        "boundary": (
            "Converts classifier predicted probabilities into a v0.2 custom_signal artifact. "
            "It does not run research validation or execute live trades."
        ),
    }
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
