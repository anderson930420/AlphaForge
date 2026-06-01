#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.crsp_sklearn_baseline import run_walk_forward_sklearn_baseline, require_sklearn
from alphaforge.json_utils import write_json_artifact
from alphaforge.parquet_io import write_parquet_artifact


SUMMARY_FILENAME = "summary.json"
WINDOW_METRICS_FILENAME = "window_metrics.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a CRSP walk-forward sklearn baseline from existing split artifacts."
    )
    parser.add_argument("--splits-dir", required=True, type=Path, help="Directory containing walk-forward split windows")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for baseline artifacts")
    parser.add_argument(
        "--model",
        default="ridge",
        choices=("ridge", "linear", "random_forest"),
        help="Sklearn regression model to train per walk-forward window",
    )
    parser.add_argument(
        "--feature-cols",
        default=None,
        type=str,
        help="Optional comma-separated feature columns. Defaults to the CRSP baseline feature set.",
    )
    parser.add_argument(
        "--feature-columns-json",
        default=None,
        type=Path,
        help="Optional JSON file containing a feature_columns list, typically written by preprocessing.",
    )
    parser.add_argument("--label-col", default="forward_1m_total_ret", help="Target label column name")
    parser.add_argument("--quantile", type=float, default=0.1, help="Cross-sectional long/short quantile")
    parser.add_argument("--random-state", type=int, default=0, help="Random seed for deterministic models")
    return parser


def parse_feature_cols(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    feature_cols = [col.strip() for col in raw.split(",") if col.strip()]
    if not feature_cols:
        raise ValueError("--feature-cols was provided but no valid feature columns were parsed")
    return feature_cols


def load_feature_columns_json(path: Path | None) -> list[str] | None:
    if path is None:
        return None

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--feature-columns-json must contain a JSON object")

    feature_columns = payload.get("feature_columns")
    if not isinstance(feature_columns, list) or not feature_columns:
        raise ValueError("--feature-columns-json must contain a non-empty feature_columns list")
    if not all(isinstance(column, str) and column for column in feature_columns):
        raise ValueError("feature_columns entries must be non-empty strings")

    count = payload.get("count")
    if count is not None and int(count) != len(feature_columns):
        raise ValueError("feature_columns count does not match the feature_columns list length")

    return list(feature_columns)


def main() -> None:
    require_sklearn()
    args = build_parser().parse_args()

    try:
        feature_cols = load_feature_columns_json(args.feature_columns_json)
        if feature_cols is None:
            feature_cols = parse_feature_cols(args.feature_cols)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_walk_forward_sklearn_baseline(
        args.splits_dir,
        model_name=args.model,
        feature_cols=feature_cols,
        label_col=args.label_col,
        quantile=args.quantile,
        random_state=args.random_state,
    )

    predictions_path = output_dir / "predictions.parquet"
    window_metrics_path = output_dir / WINDOW_METRICS_FILENAME
    portfolio_path = output_dir / "prediction_portfolio_returns.parquet"
    summary_path = output_dir / SUMMARY_FILENAME

    write_parquet_artifact(result["predictions"], predictions_path, index=False)
    write_parquet_artifact(result["portfolio_returns"], portfolio_path, index=False)

    window_metrics_payload = {
        "status": "ok",
        "stage": "crsp_sklearn_baseline",
        "splits_dir": str(args.splits_dir),
        "model_name": args.model,
        "feature_cols": feature_cols if feature_cols is not None else result["summary"]["feature_cols"],
        "label_col": args.label_col,
        "quantile": float(args.quantile),
        "random_state": int(args.random_state),
        "window_count": int(len(result["window_metrics"])),
        "window_metrics": result["window_metrics"],
    }
    write_json_artifact(window_metrics_path, window_metrics_payload)

    summary = {
        **result["summary"],
        "output_dir": str(output_dir),
        "paths": {
            "predictions": str(predictions_path),
            "window_metrics": str(window_metrics_path),
            "prediction_portfolio_returns": str(portfolio_path),
            "summary": str(summary_path),
        },
    }
    write_json_artifact(summary_path, summary)

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
