#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge.classification_labels import DEFAULT_CLASSIFICATION_LABEL_COL, build_binary_return_classification_labels
from alphaforge.json_utils import write_json_artifact
from alphaforge.ml_classifiers import (
    SUPPORTED_CLASSIFIERS,
    evaluate_classifier_predictions,
    fit_sklearn_classifier,
    predict_sklearn_classifier,
    write_classifier_artifacts,
)
from alphaforge.ml_dataset import build_ml_dataset, time_train_test_split
from alphaforge.ml_models import _require_sklearn
from alphaforge.return_labels import build_forward_return_labels, join_features_with_return_labels, load_return_panel


SUMMARY_FILENAME = "classifier_baseline_summary.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a sklearn classification baseline from features and return labels."
    )
    parser.add_argument("--features", required=True, type=Path)
    parser.add_argument("--returns", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--classifier", required=True, choices=sorted(SUPPORTED_CLASSIFIERS))
    parser.add_argument("--feature-cols", required=True, help="Comma-separated feature column names")
    parser.add_argument("--return-label-col", default="ret_fwd_1m")
    parser.add_argument("--classification-label-col", default=DEFAULT_CLASSIFICATION_LABEL_COL)
    parser.add_argument("--classification-threshold", type=float, default=0.0)
    parser.add_argument("--train-end", required=True)
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
    feature_cols = [column.strip() for column in args.feature_cols.split(",") if column.strip()]

    returns_df = load_return_panel(args.returns)
    features_df = load_return_panel(args.features)
    return_labels = build_forward_return_labels(
        returns_df,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        return_col=args.return_col,
        horizon_months=args.horizon_months,
        label_col=args.return_label_col,
    )
    return_labels_path = output_dir / "return_labels.csv"
    return_labels.to_csv(return_labels_path, index=False)

    classification_labels = build_binary_return_classification_labels(
        return_labels,
        return_col=args.return_label_col,
        label_col=args.classification_label_col,
        threshold=args.classification_threshold,
    )
    classification_labels_path = output_dir / "classification_labels.csv"
    classification_labels.to_csv(classification_labels_path, index=False)

    supervised_panel = join_features_with_return_labels(
        features_df,
        classification_labels,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
    )
    supervised_panel_path = output_dir / "supervised_classifier_panel.csv"
    supervised_panel.to_csv(supervised_panel_path, index=False)

    dataset = build_ml_dataset(
        supervised_panel,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
        label_col=args.classification_label_col,
        feature_cols=feature_cols,
        drop_missing_label=True,
        drop_missing_features=False,
    )
    train_df, test_df = time_train_test_split(
        dataset,
        date_col=args.date_col,
        train_end=args.train_end,
    )

    classifier_pack = fit_sklearn_classifier(
        train_df,
        classifier_name=args.classifier,
        feature_cols=feature_cols,
        label_col=args.classification_label_col,
        random_state=args.random_state,
    )
    predictions = predict_sklearn_classifier(
        classifier_pack,
        test_df,
        asset_id_col=args.asset_id_col,
        date_col=args.date_col,
    )
    metrics = evaluate_classifier_predictions(
        predictions,
        label_col=args.classification_label_col,
    )

    classifier_dir = output_dir / "classifier"
    train_config = {
        "classifier_name": args.classifier,
        "feature_cols": feature_cols,
        "return_label_col": args.return_label_col,
        "classification_label_col": args.classification_label_col,
        "classification_threshold": args.classification_threshold,
        "asset_id_col": args.asset_id_col,
        "date_col": args.date_col,
        "train_end": args.train_end,
        "random_state": args.random_state,
    }
    artifact_paths = write_classifier_artifacts(
        classifier_dir,
        classifier_pack=classifier_pack,
        predictions=predictions,
        metrics=metrics,
        train_df=train_df,
        test_df=test_df,
        train_config=train_config,
    )

    summary = {
        "status": "ok",
        "stage": "sklearn_classifier_baseline",
        "classifier": args.classifier,
        "feature_cols": feature_cols,
        "return_labels_rows": int(len(return_labels)),
        "classification_labels_rows": int(len(classification_labels)),
        "supervised_panel_rows": int(len(supervised_panel)),
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "classification_threshold": args.classification_threshold,
        "classification_label_col": args.classification_label_col,
        "metrics": metrics,
        "does_generate_trading_signal": False,
        "does_run_research_validation": False,
        "does_execute_live_trades": False,
        "paths": {
            "return_labels": str(return_labels_path),
            "classification_labels": str(classification_labels_path),
            "supervised_panel": str(supervised_panel_path),
            "classifier_dir": str(classifier_dir),
            **{key: str(value) for key, value in artifact_paths.items()},
        },
        "boundary": (
            "Builds binary forward-return classification labels and sklearn classifier artifacts. "
            "It does not convert probabilities into trading signals or run research validation."
        ),
    }
    summary_path = output_dir / SUMMARY_FILENAME
    write_json_artifact(summary_path, summary)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
