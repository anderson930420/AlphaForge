#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.ml_dataset import build_ml_dataset, time_train_test_split
from alphaforge.ml_diagnostics import (
    run_ml_prediction_diagnostics,
    write_ml_prediction_diagnostics,
)
from alphaforge.ml_models import (
    _require_sklearn,
    evaluate_sklearn_predictions,
    fit_sklearn_model,
    predict_sklearn_model,
    write_artifacts,
)
from alphaforge.ml_signal import build_ml_prediction_signal
from alphaforge.return_labels import (
    build_forward_return_labels,
    join_features_with_return_labels,
    load_return_panel,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local ML demo pipeline: features + returns → predictions + diagnostics + signal"
    )
    parser.add_argument("--features", required=True, type=Path, help="Path to features CSV")
    parser.add_argument("--returns", required=True, type=Path, help="Path to monthly returns CSV")
    parser.add_argument("--output-dir", required=True, type=Path, help="Output directory for pipeline artifacts")
    parser.add_argument("--model", required=True, type=str, help="Sklearn model name (e.g. ridge_regressor)")
    parser.add_argument("--feature-cols", required=True, type=str, help="Comma-separated feature column names")
    parser.add_argument("--label-col", default="ret_fwd_1m")
    parser.add_argument("--train-end", required=True, type=str, help="Train/test split date (YYYY-MM-DD)")
    parser.add_argument("--long-quantile", type=float, default=0.8)
    parser.add_argument("--short-quantile", type=float, default=0.2)
    parser.add_argument("--diagnostic-quantiles", type=int, default=5)
    parser.add_argument("--asset-id-col", default="asset_id")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--return-col", default="ret")
    parser.add_argument("--horizon-months", type=int, default=1)
    parser.add_argument("--random-state", type=int, default=42)
    return parser


def main() -> None:
    _require_sklearn()
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    feature_cols = [c.strip() for c in args.feature_cols.split(",")]

    returns_df = load_return_panel(args.returns)
    features_df = load_return_panel(args.features)

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

    supervised_panel = join_features_with_return_labels(
        features_df,
        return_labels,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
    )
    supervised_panel_path = output_dir / "supervised_panel.csv"
    supervised_panel.to_csv(supervised_panel_path, index=False)

    model_dir = output_dir / "model"
    model_dir.mkdir(parents=True, exist_ok=True)

    dataset = build_ml_dataset(
        supervised_panel,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        label_col=args.label_col,
        feature_cols=feature_cols,
        drop_missing_label=True,
        drop_missing_features=False,
    )

    train_df, test_df = time_train_test_split(
        dataset,
        date_col=args.date_col,
        train_end=args.train_end,
    )

    model_pack = fit_sklearn_model(
        train_df,
        model_name=args.model,
        feature_cols=feature_cols,
        label_col=args.label_col,
        random_state=args.random_state,
    )

    predictions = predict_sklearn_model(
        model_pack,
        test_df,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
    )

    metrics = evaluate_sklearn_predictions(
        predictions,
        label_col=args.label_col,
    )

    train_config = {
        "model_name": args.model,
        "label_col": args.label_col,
        "train_end": args.train_end,
        "feature_cols": feature_cols,
        "asset_id_col": args.asset_id_col,
        "date_col": args.date_col,
        "random_state": args.random_state,
    }

    write_artifacts(
        model_dir,
        model_pack=model_pack,
        predictions=predictions,
        metrics=metrics,
        train_df=train_df,
        test_df=test_df,
        train_config=train_config,
    )

    diagnostics_dir = output_dir / "ml_prediction_diagnostics"
    diagnostics_result = run_ml_prediction_diagnostics(
        predictions,
        prediction_col="predicted_return",
        label_col=args.label_col,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        quantiles=args.diagnostic_quantiles,
    )
    write_ml_prediction_diagnostics(diagnostics_result, diagnostics_dir)

    signal_dir = output_dir / "signal"
    signal_dir.mkdir(parents=True, exist_ok=True)

    ml_signal = build_ml_prediction_signal(
        predictions,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        prediction_col="predicted_return",
        long_quantile=args.long_quantile,
        short_quantile=args.short_quantile,
    )
    ml_signal_path = signal_dir / "ml_signal.csv"
    ml_signal.to_csv(ml_signal_path, index=False)

    ml_demo_summary = {
        "status": "ok",
        "output_dir": str(output_dir),
        "model": args.model,
        "feature_cols": feature_cols,
        "return_labels_rows": int(len(return_labels)),
        "supervised_panel_rows": int(len(supervised_panel)),
        "predictions_rows": int(len(predictions)),
        "ml_signal_rows": int(len(ml_signal)),
        "paths": {
            "return_labels": str(return_labels_path),
            "supervised_panel": str(supervised_panel_path),
            "model_dir": str(model_dir),
            "diagnostics_dir": str(diagnostics_dir),
            "signal_file": str(ml_signal_path),
        },
        "boundary_note": (
            "This is a research/demo artifact generation pipeline. "
            "It does not perform profitability validation, live trading, "
            "or a full backtest/research-validate cycle."
        ),
    }
    summary_path = output_dir / "ml_demo_summary.json"
    with open(summary_path, "w") as f:
        json.dump(ml_demo_summary, f, indent=2, default=str)

    print(json.dumps(ml_demo_summary, indent=2, default=str))


if __name__ == "__main__":
    main()
