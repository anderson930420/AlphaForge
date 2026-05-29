#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.artifact_report import render_artifact_report
from alphaforge.ml_baseline import (
    evaluate_regression_predictions,
    fit_baseline_regressor,
    predict_baseline_regressor,
)
from alphaforge.ml_dataset import build_ml_dataset, time_train_test_split
from alphaforge.ml_signal import build_ml_prediction_signal
from alphaforge.return_labels import (
    build_forward_return_labels,
    join_features_with_return_labels,
    load_return_panel,
)


DEFAULT_FEATURE_COLS = "Mom12m,BM"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="End-to-end ML artifact smoke: features + returns -> ML signal + report"
    )
    parser.add_argument("--features", required=True, type=Path)
    parser.add_argument("--returns", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--asset-id-col", default="asset_id")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--return-col", default="ret")
    parser.add_argument("--label-col", default="ret_fwd_1m")
    parser.add_argument("--horizon-months", type=int, default=1)
    parser.add_argument("--feature-cols", default=DEFAULT_FEATURE_COLS)
    parser.add_argument("--train-end", default="2024-02-29")
    parser.add_argument("--test-start", default=None)
    parser.add_argument("--prediction-col", default="predicted_return")
    parser.add_argument("--long-quantile", type=float, default=0.8)
    parser.add_argument("--short-quantile", type=float, default=0.2)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    feature_cols = [c.strip() for c in args.feature_cols.split(",")]

    returns_df = load_return_panel(args.returns)

    return_labels = build_forward_return_labels(
        returns_df,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        return_col=args.return_col,
        horizon_months=args.horizon_months,
        label_col=args.label_col,
    )
    return_labels_path = output_dir / "return_labels.csv"
    return_labels.to_csv(return_labels_path, index=False)

    features_df = load_return_panel(args.features)
    supervised_panel = join_features_with_return_labels(
        features_df,
        return_labels,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
    )
    supervised_panel_path = output_dir / "supervised_panel.csv"
    supervised_panel.to_csv(supervised_panel_path, index=False)

    dataset = build_ml_dataset(
        supervised_panel,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        label_col=args.label_col,
        feature_cols=feature_cols,
        drop_missing_label=True,
    )
    dataset_path = output_dir / "dataset.csv"
    dataset.to_csv(dataset_path, index=False)

    train_df, test_df = time_train_test_split(
        dataset,
        date_col=args.date_col,
        train_end=args.train_end,
        test_start=args.test_start,
    )

    model = fit_baseline_regressor(
        train_df,
        feature_cols=feature_cols,
        label_col=args.label_col,
    )

    predictions = predict_baseline_regressor(
        model,
        test_df,
        feature_cols=feature_cols,
        prediction_col=args.prediction_col,
        label_col=args.label_col,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
    )
    predictions_path = output_dir / "predictions.csv"
    predictions.to_csv(predictions_path, index=False)

    metrics = evaluate_regression_predictions(
        predictions,
        label_col=args.label_col,
        prediction_col=args.prediction_col,
    )
    metrics_path = output_dir / "metrics_summary.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    ml_signal = build_ml_prediction_signal(
        predictions,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        prediction_col=args.prediction_col,
        long_quantile=args.long_quantile,
        short_quantile=args.short_quantile,
    )
    ml_signal_path = output_dir / "ml_signal.csv"
    ml_signal.to_csv(ml_signal_path, index=False)

    report_path = render_artifact_report(artifact_dir=output_dir)

    summary = {
        "status": "ok",
        "output_dir": str(output_dir),
        "return_labels_rows": int(len(return_labels)),
        "supervised_panel_rows": int(len(supervised_panel)),
        "dataset_rows": int(len(dataset)),
        "predictions_rows": int(len(predictions)),
        "ml_signal_rows": int(len(ml_signal)),
        "metrics_path": str(metrics_path),
        "ml_signal_path": str(ml_signal_path),
        "report_path": report_path,
    }
    summary_path = output_dir / "smoke_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
