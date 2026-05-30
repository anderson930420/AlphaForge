#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from alphaforge import config
from alphaforge.backtest import SIGNED_EXECUTION_SEMANTICS, SUPPORTED_EXECUTION_SEMANTICS
from alphaforge.data_loader import load_market_data
from alphaforge.experiment_runner import run_research_validation_protocol_with_details
from alphaforge.json_utils import write_json_artifact
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
from alphaforge.ml_signal import ML_SIGNAL_SIGNAL_COLUMNS, build_ml_prediction_signal
from alphaforge.return_labels import (
    build_forward_return_labels,
    join_features_with_return_labels,
    load_return_panel,
)
from alphaforge.schemas import BacktestConfig, DataSpec, ResearchPeriod, ResearchValidationConfig, WalkForwardConfig
from alphaforge.storage import serialize_research_protocol_artifact_receipt, serialize_research_protocol_summary


DEFAULT_ML_SIGNAL_NAME = "ml_predicted_return"
RESEARCH_VALIDATION_SUMMARY_FILENAME = "ml_demo_research_validation_summary.json"


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
    parser.add_argument(
        "--run-research-validation",
        action="store_true",
        help="Optionally project the generated ML signal to one symbol and run custom_signal research validation.",
    )
    parser.add_argument("--research-validation-market-data", type=Path, default=None)
    parser.add_argument("--research-validation-symbol", default=None)
    parser.add_argument("--research-validation-signal-name", default=DEFAULT_ML_SIGNAL_NAME)
    parser.add_argument("--research-validation-datetime-column", default="datetime")
    parser.add_argument("--research-validation-development-start", default=None)
    parser.add_argument("--research-validation-development-end", default=None)
    parser.add_argument("--research-validation-holdout-start", default=None)
    parser.add_argument("--research-validation-holdout-end", default=None)
    parser.add_argument("--research-validation-train-size", type=int, default=2)
    parser.add_argument("--research-validation-test-size", type=int, default=1)
    parser.add_argument("--research-validation-step-size", type=int, default=1)
    parser.add_argument("--research-validation-experiment-name", default="ml_signal_single_symbol_validation")
    parser.add_argument("--research-validation-initial-capital", type=float, default=config.INITIAL_CAPITAL)
    parser.add_argument("--research-validation-fee-rate", type=float, default=config.DEFAULT_FEE_RATE)
    parser.add_argument("--research-validation-slippage-rate", type=float, default=config.DEFAULT_SLIPPAGE_RATE)
    parser.add_argument("--research-validation-annualization-factor", type=int, default=config.DEFAULT_ANNUALIZATION)
    parser.add_argument(
        "--research-validation-execution-semantics",
        choices=SUPPORTED_EXECUTION_SEMANTICS,
        default=SIGNED_EXECUTION_SEMANTICS,
    )
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
        signal_name=DEFAULT_ML_SIGNAL_NAME,
        long_quantile=args.long_quantile,
        short_quantile=args.short_quantile,
    )
    ml_signal_path = signal_dir / "ml_signal.csv"
    ml_signal.to_csv(ml_signal_path, index=False)

    research_validation_summary = _run_optional_research_validation(
        args=args,
        output_dir=output_dir,
        ml_signal=ml_signal,
        ml_signal_path=ml_signal_path,
    )

    ml_demo_summary = {
        "status": "ok",
        "output_dir": str(output_dir),
        "model": args.model,
        "feature_cols": feature_cols,
        "return_labels_rows": int(len(return_labels)),
        "supervised_panel_rows": int(len(supervised_panel)),
        "predictions_rows": int(len(predictions)),
        "ml_signal_rows": int(len(ml_signal)),
        "does_run_research_validation": research_validation_summary is not None,
        "research_validation": research_validation_summary,
        "paths": {
            "return_labels": str(return_labels_path),
            "supervised_panel": str(supervised_panel_path),
            "model_dir": str(model_dir),
            "diagnostics_dir": str(diagnostics_dir),
            "signal_file": str(ml_signal_path),
            "research_validation_summary": None
            if research_validation_summary is None
            else research_validation_summary["paths"]["summary"],
        },
        "boundary_note": _build_boundary_note(research_validation_summary is not None),
    }
    summary_path = output_dir / "ml_demo_summary.json"
    write_json_artifact(summary_path, ml_demo_summary)

    print(json.dumps(ml_demo_summary, indent=2, default=str))


def _run_optional_research_validation(
    *,
    args: argparse.Namespace,
    output_dir: Path,
    ml_signal: pd.DataFrame,
    ml_signal_path: Path,
) -> dict[str, object] | None:
    if not args.run_research_validation:
        return None
    _validate_research_validation_args(args)

    research_root = output_dir / "research_validation"
    derived_signal_dir = research_root / "derived_signal"
    derived_signal_dir.mkdir(parents=True, exist_ok=True)

    projected_signal = _project_single_symbol_signal(
        ml_signal,
        symbol=args.research_validation_symbol,
        signal_name=args.research_validation_signal_name,
    )
    projected_signal_path = derived_signal_dir / "single_symbol_signal.csv"
    projected_signal.to_csv(projected_signal_path, index=False)

    data_spec = DataSpec(
        path=args.research_validation_market_data,
        symbol=args.research_validation_symbol,
        datetime_column=args.research_validation_datetime_column,
    )
    market_data = load_market_data(data_spec)
    date_alignment = _validate_signal_market_alignment(projected_signal, market_data)

    nonzero_target_weight_count = int((projected_signal["target_weight"].astype(float).abs() > 0.0).sum())
    warnings = []
    if nonzero_target_weight_count == 0:
        warnings.append("Selected symbol is all-flat under this signal; demo validation may be uninformative.")

    research_config = ResearchValidationConfig(
        data_spec=data_spec,
        strategy_name="custom_signal",
        parameter_grid={},
        development_period=ResearchPeriod(
            start=args.research_validation_development_start,
            end=args.research_validation_development_end,
        ),
        holdout_period=ResearchPeriod(
            start=args.research_validation_holdout_start,
            end=args.research_validation_holdout_end,
        ),
        walk_forward_config=WalkForwardConfig(
            train_size=args.research_validation_train_size,
            test_size=args.research_validation_test_size,
            step_size=args.research_validation_step_size,
        ),
        backtest_config=BacktestConfig(
            initial_capital=args.research_validation_initial_capital,
            fee_rate=args.research_validation_fee_rate,
            slippage_rate=args.research_validation_slippage_rate,
            annualization_factor=args.research_validation_annualization_factor,
            execution_semantics=args.research_validation_execution_semantics,
        ),
        output_dir=research_root,
        experiment_name=args.research_validation_experiment_name,
        signal_file=projected_signal_path,
        signal_name=args.research_validation_signal_name,
    )
    execution = run_research_validation_protocol_with_details(research_config)
    artifact_receipt = serialize_research_protocol_artifact_receipt(execution.artifact_receipt)

    summary = {
        "status": "ok",
        "stage": "ml_demo_optional_research_validation",
        "validation_mode": "single_symbol_projection",
        "source_signal_path": str(ml_signal_path),
        "derived_single_symbol_signal_path": str(projected_signal_path),
        "market_data_path": str(args.research_validation_market_data),
        "symbol": args.research_validation_symbol,
        "signal_name": args.research_validation_signal_name,
        "source_signal_row_count": int(len(ml_signal)),
        "selected_signal_row_count": int(len(projected_signal)),
        "nonzero_target_weight_count": nonzero_target_weight_count,
        "all_flat_selected_symbol": nonzero_target_weight_count == 0,
        "date_alignment": date_alignment,
        "warnings": warnings,
        "does_train_model": False,
        "does_generate_predictions": False,
        "does_add_multi_symbol_backtest": False,
        "does_execute_live_trades": False,
        "research_validation_artifact_receipt": artifact_receipt,
        "research_validation_summary": serialize_research_protocol_summary(execution.research_protocol_summary),
        "paths": {
            "summary": str(research_root / RESEARCH_VALIDATION_SUMMARY_FILENAME),
            "derived_single_symbol_signal": str(projected_signal_path),
            "research_protocol_summary": None
            if artifact_receipt is None
            else artifact_receipt.get("research_protocol_summary_path"),
        },
    }
    write_json_artifact(research_root / RESEARCH_VALIDATION_SUMMARY_FILENAME, summary)
    return summary


def _validate_research_validation_args(args: argparse.Namespace) -> None:
    required = {
        "research_validation_market_data": "--research-validation-market-data",
        "research_validation_symbol": "--research-validation-symbol",
        "research_validation_development_start": "--research-validation-development-start",
        "research_validation_development_end": "--research-validation-development-end",
        "research_validation_holdout_start": "--research-validation-holdout-start",
        "research_validation_holdout_end": "--research-validation-holdout-end",
    }
    missing = [flag for attr, flag in required.items() if getattr(args, attr) is None]
    if missing:
        raise ValueError("--run-research-validation requires: " + ", ".join(missing))


def _project_single_symbol_signal(ml_signal: pd.DataFrame, *, symbol: str, signal_name: str) -> pd.DataFrame:
    missing = [column for column in ML_SIGNAL_SIGNAL_COLUMNS if column not in ml_signal.columns]
    if missing:
        raise ValueError(f"Missing required ML signal columns: {missing}")
    selected = ml_signal.copy()
    selected = selected.loc[selected["signal_name"].astype(str) == str(signal_name)].copy()
    if selected.empty:
        raise ValueError(f"ml_signal.csv does not contain requested signal_name {signal_name!r}")
    selected = selected.loc[selected["symbol"].astype(str) == str(symbol)].copy()
    if selected.empty:
        raise ValueError(f"No signal rows found for symbol {symbol!r}")
    selected["datetime"] = _normalize_daily_dates(selected["datetime"])
    selected["available_at"] = _normalize_daily_dates(selected["available_at"])
    selected = selected.sort_values(["datetime", "signal_name"], kind="mergesort").reset_index(drop=True)
    return selected.reindex(columns=ML_SIGNAL_SIGNAL_COLUMNS)


def _validate_signal_market_alignment(signal: pd.DataFrame, market_data: pd.DataFrame) -> dict[str, object]:
    signal_dates = pd.Index(_normalize_daily_dates(signal["datetime"]).dropna().unique())
    market_dates = pd.Index(_normalize_daily_dates(market_data["datetime"]).dropna().unique())
    extra_signal_dates = signal_dates.difference(market_dates)
    if len(extra_signal_dates):
        formatted = [str(pd.Timestamp(value).date()) for value in extra_signal_dates]
        raise ValueError(
            f"Selected signal contains dates not present in market_data: {formatted}. "
            "custom_signal validation requires signal datetime values to be a subset of market_data datetime."
        )
    return {
        "signal_date_count": int(len(signal_dates)),
        "market_date_count": int(len(market_dates)),
        "extra_signal_dates": [],
    }


def _normalize_daily_dates(values: pd.Series) -> pd.Series:
    def normalize(value: object) -> pd.Timestamp:
        if pd.isna(value):
            return pd.NaT
        parsed = pd.to_datetime(value, errors="raise")
        return pd.Timestamp(parsed.date())

    return values.map(normalize)


def _build_boundary_note(ran_research_validation: bool) -> str:
    if ran_research_validation:
        return (
            "This is a research/demo artifact generation pipeline with optional one-symbol custom_signal "
            "research validation enabled. It does not perform live trading or multi-symbol portfolio validation."
        )
    return (
        "This is a research/demo artifact generation pipeline. "
        "It does not perform profitability validation, live trading, "
        "or a full backtest/research-validate cycle unless --run-research-validation is enabled."
    )


if __name__ == "__main__":
    main()
