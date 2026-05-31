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
from alphaforge.ml_signal import ML_SIGNAL_SIGNAL_COLUMNS, build_classifier_probability_signal, load_prediction_panel
from alphaforge.schemas import BacktestConfig, DataSpec, ResearchPeriod, ResearchValidationConfig, WalkForwardConfig
from alphaforge.storage import serialize_research_protocol_artifact_receipt, serialize_research_protocol_summary


DEFAULT_CLASSIFIER_SIGNAL_NAME = "ml_predicted_probability"
RESEARCH_VALIDATION_SUMMARY_FILENAME = "ml_demo_research_validation_summary.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert classifier probability predictions to a v0.2 custom_signal, project one symbol, "
            "and run the existing custom_signal research-validation protocol."
        )
    )
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--market-data", required=True, type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--asset-id-col", default="asset_id")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--probability-col", default="predicted_probability")
    parser.add_argument("--symbol-col", default=None)
    parser.add_argument("--available-at-col", default=None)
    parser.add_argument("--signal-name", default=DEFAULT_CLASSIFIER_SIGNAL_NAME)
    parser.add_argument("--source", default="AlphaForgeMLClassifier")
    parser.add_argument("--long-probability-threshold", type=float, default=0.6)
    parser.add_argument("--short-probability-threshold", type=float, default=0.4)
    parser.add_argument("--gross-long-weight", type=float, default=1.0)
    parser.add_argument("--gross-short-weight", type=float, default=-1.0)
    parser.add_argument("--datetime-column", default="datetime")
    parser.add_argument("--development-start", required=True)
    parser.add_argument("--development-end", required=True)
    parser.add_argument("--holdout-start", required=True)
    parser.add_argument("--holdout-end", required=True)
    parser.add_argument("--train-size", type=int, default=2)
    parser.add_argument("--test-size", type=int, default=1)
    parser.add_argument("--step-size", type=int, default=1)
    parser.add_argument("--experiment-name", default="ml_signal_single_symbol_validation")
    parser.add_argument("--initial-capital", type=float, default=config.INITIAL_CAPITAL)
    parser.add_argument("--fee-rate", type=float, default=config.DEFAULT_FEE_RATE)
    parser.add_argument("--slippage-rate", type=float, default=config.DEFAULT_SLIPPAGE_RATE)
    parser.add_argument("--annualization-factor", type=int, default=config.DEFAULT_ANNUALIZATION)
    parser.add_argument(
        "--execution-semantics",
        choices=SUPPORTED_EXECUTION_SEMANTICS,
        default=SIGNED_EXECUTION_SEMANTICS,
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    model_dir = output_dir / "model"
    signal_dir = output_dir / "signal"
    research_root = output_dir / "research_validation"
    derived_signal_dir = research_root / "derived_signal"
    for path in (output_dir, model_dir, signal_dir, research_root, derived_signal_dir):
        path.mkdir(parents=True, exist_ok=True)

    predictions = load_prediction_panel(args.predictions)
    predictions_path = model_dir / "predictions.csv"
    predictions.to_csv(predictions_path, index=False)

    classifier_signal = build_classifier_probability_signal(
        predictions,
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
    signal_path = signal_dir / "ml_signal.csv"
    classifier_signal.to_csv(signal_path, index=False)

    projected_signal = _project_single_symbol_signal(
        classifier_signal,
        symbol=args.symbol,
        signal_name=args.signal_name,
    )
    projected_signal_path = derived_signal_dir / "single_symbol_signal.csv"
    projected_signal.to_csv(projected_signal_path, index=False)

    data_spec = DataSpec(path=args.market_data, symbol=args.symbol, datetime_column=args.datetime_column)
    market_data = load_market_data(data_spec)
    date_alignment = _validate_signal_market_alignment(projected_signal, market_data)
    nonzero_target_weight_count = int((projected_signal["target_weight"].astype(float).abs() > 0.0).sum())
    warnings = []
    if nonzero_target_weight_count == 0:
        warnings.append("Selected symbol is all-flat under this classifier signal; demo validation may be uninformative.")

    research_config = ResearchValidationConfig(
        data_spec=data_spec,
        strategy_name="custom_signal",
        parameter_grid={},
        development_period=ResearchPeriod(start=args.development_start, end=args.development_end),
        holdout_period=ResearchPeriod(start=args.holdout_start, end=args.holdout_end),
        walk_forward_config=WalkForwardConfig(
            train_size=args.train_size,
            test_size=args.test_size,
            step_size=args.step_size,
        ),
        backtest_config=BacktestConfig(
            initial_capital=args.initial_capital,
            fee_rate=args.fee_rate,
            slippage_rate=args.slippage_rate,
            annualization_factor=args.annualization_factor,
            execution_semantics=args.execution_semantics,
        ),
        output_dir=research_root,
        experiment_name=args.experiment_name,
        signal_file=projected_signal_path,
        signal_name=args.signal_name,
    )
    execution = run_research_validation_protocol_with_details(research_config)
    artifact_receipt = serialize_research_protocol_artifact_receipt(execution.artifact_receipt)
    research_summary_payload = serialize_research_protocol_summary(execution.research_protocol_summary)

    research_validation_summary = {
        "status": "ok",
        "stage": "classifier_signal_research_validation_demo",
        "validation_mode": "single_symbol_projection",
        "source_signal_path": str(signal_path),
        "derived_single_symbol_signal_path": str(projected_signal_path),
        "market_data_path": str(args.market_data),
        "symbol": args.symbol,
        "signal_name": args.signal_name,
        "source_signal_row_count": int(len(classifier_signal)),
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
        "research_validation_summary": research_summary_payload,
        "paths": {
            "summary": str(research_root / RESEARCH_VALIDATION_SUMMARY_FILENAME),
            "derived_single_symbol_signal": str(projected_signal_path),
            "research_protocol_summary": None
            if artifact_receipt is None
            else artifact_receipt.get("research_protocol_summary_path"),
        },
    }
    write_json_artifact(research_root / RESEARCH_VALIDATION_SUMMARY_FILENAME, research_validation_summary)

    demo_summary = {
        "status": "ok",
        "stage": "classifier_signal_research_validation_demo",
        "output_dir": str(output_dir),
        "model": "classifier_probability_signal",
        "predictions_rows": int(len(predictions)),
        "ml_signal_rows": int(len(classifier_signal)),
        "does_run_research_validation": True,
        "research_validation": research_validation_summary,
        "long_probability_threshold": args.long_probability_threshold,
        "short_probability_threshold": args.short_probability_threshold,
        "paths": {
            "predictions": str(predictions_path),
            "signal_file": str(signal_path),
            "research_validation_summary": str(research_root / RESEARCH_VALIDATION_SUMMARY_FILENAME),
        },
        "boundary_note": (
            "This demo consumes existing classifier probability predictions, converts them to a v0.2 custom_signal, "
            "projects one symbol, and runs the existing custom_signal research-validation protocol. It does not train "
            "a classifier, select optimal thresholds, perform multi-symbol portfolio validation, or execute live trades."
        ),
    }
    summary_path = output_dir / "ml_demo_summary.json"
    write_json_artifact(summary_path, demo_summary)
    print(json.dumps(demo_summary, indent=2, default=str))


def _project_single_symbol_signal(signal: pd.DataFrame, *, symbol: str, signal_name: str) -> pd.DataFrame:
    missing = [column for column in ML_SIGNAL_SIGNAL_COLUMNS if column not in signal.columns]
    if missing:
        raise ValueError(f"Missing required ML signal columns: {missing}")
    selected = signal.copy()
    selected = selected.loc[selected["signal_name"].astype(str) == str(signal_name)].copy()
    if selected.empty:
        raise ValueError(f"classifier signal does not contain requested signal_name {signal_name!r}")
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


if __name__ == "__main__":
    main()
