#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from alphaforge.ml_models import run_sklearn_ml_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train an sklearn regression model on a supervised feature-label panel"
    )
    parser.add_argument("--panel", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", required=True, type=str)
    parser.add_argument("--label-col", default="ret_fwd_1m")
    parser.add_argument("--train-end", required=True, type=str)
    parser.add_argument("--feature-cols", default=None, type=str)
    parser.add_argument("--asset-id-col", default="asset_id")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--random-state", type=int, default=42)
    return parser


def parse_feature_cols(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    feature_cols = [col.strip() for col in raw.split(",") if col.strip()]
    if not feature_cols:
        raise ValueError("--feature-cols was provided but no valid feature columns were parsed")
    return feature_cols


def main() -> None:
    args = build_parser().parse_args()

    try:
        feature_cols = parse_feature_cols(args.feature_cols)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    panel_df = pd.read_csv(args.panel)

    artifacts = run_sklearn_ml_model(
        panel_df,
        model_name=args.model,
        output_dir=Path(args.output_dir),
        label_col=args.label_col,
        train_end=args.train_end,
        feature_cols=feature_cols,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        random_state=args.random_state,
    )

    summary = {
        "status": "ok",
        "model": args.model,
        "output_dir": str(args.output_dir),
        "artifacts": {k: str(v) for k, v in artifacts.items()},
    }
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
