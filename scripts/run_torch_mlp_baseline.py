#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from alphaforge.ml_torch import run_torch_mlp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train a PyTorch MLP regression baseline on a supervised feature-label panel"
    )
    parser.add_argument("--panel", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--label-col", default="ret_fwd_1m")
    parser.add_argument("--train-end", required=True, type=str)
    parser.add_argument("--feature-cols", default=None, type=str)
    parser.add_argument("--asset-id-col", default="asset_id")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--weight-decay", type=float, default=0.0001)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    feature_cols: list[str] | None = None
    if args.feature_cols is not None:
        feature_cols = [c.strip() for c in args.feature_cols.split(",")]

    panel_df = pd.read_csv(args.panel)

    artifacts = run_torch_mlp(
        panel_df,
        output_dir=Path(args.output_dir),
        label_col=args.label_col,
        train_end=args.train_end,
        feature_cols=feature_cols,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        hidden_dim=args.hidden_dim,
        dropout=args.dropout,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        seed=args.seed,
    )

    summary = {
        "status": "ok",
        "output_dir": str(args.output_dir),
        "artifacts": {k: str(v) for k, v in artifacts.items()},
    }
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
