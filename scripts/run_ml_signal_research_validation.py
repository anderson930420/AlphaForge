#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from alphaforge import config
from alphaforge.backtest import SIGNED_EXECUTION_SEMANTICS, SUPPORTED_EXECUTION_SEMANTICS
from alphaforge.custom_signal import V2_SIGNAL_COLUMNS
from alphaforge.data_loader import load_market_data
from alphaforge.experiment_runner import run_research_validation_protocol_with_details
from alphaforge.json_utils import write_json_artifact
from alphaforge.schemas import BacktestConfig, DataSpec, ResearchPeriod, ResearchValidationConfig, WalkForwardConfig
from alphaforge.storage import serialize_research_protocol_artifact_receipt, serialize_research_protocol_summary


SUMMARY_FILENAME = "ml_signal_research_validation_summary.json"
INPUT_SUMMARY_FILENAME = "input_summary.json"
DERIVED_SIGNAL_FILENAME = "single_symbol_signal.csv"
ALL_FLAT_WARNING = (
    "WARNING: selected symbol has zero nonzero target_weight rows. "
    "This is a valid all-flat strategy, but it is not useful for demo validation. "
    "Consider choosing another symbol with active ML signal exposure."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Project a cross-sectional AlphaForge ML signal to one symbol and validate it through "
            "the existing custom_signal research-validation protocol."
        )
    )
    parser.add_argument("--signal-file", required=True, type=Path, help="Path to a multi-symbol ML signal CSV")
    parser.add_argument("--market-data", required=True, type=Path, help="Canonical OHLCV market-data CSV")
    parser.add_argument("--symbol", required=True, help="Single symbol to validate")
    parser.add_argument("--signal-name", default=None, help="Signal name to select when the input contains multiple names")
    parser.add_argument("--output-dir", required=True, type=Path, help="Output directory for derived and validation artifacts")
    parser.add_argument("--experiment-name", default="research_validation")
    parser.add_argument("--datetime-column", default="datetime")
    parser.add_argument("--development-start", required=True)
    parser.add_argument("--development-end", required=True)
    parser.add_argument("--holdout-start", required=True)
    parser.add_argument("--holdout-end", required=True)
    parser.add_argument("--train-size", required=True, type=int)
    parser.add_argument("--test-size", required=True, type=int)
    parser.add_argument("--step-size", required=True, type=int)
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


def load_signal_frame(signal_file: Path) -> pd.DataFrame:
    frame = pd.read_csv(signal_file)
    frame = frame.rename(columns={name: name.strip().lower() for name in frame.columns})
    missing = [column for column in V2_SIGNAL_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required v0.2 signal columns: {missing}")
    return frame.copy()


def project_single_symbol_signal(
    signal_frame: pd.DataFrame,
    *,
    symbol: str,
    signal_name: str | None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    source_signal_names = _unique_non_null_values(signal_frame["signal_name"])
    if signal_name is None and len(source_signal_names) > 1:
        names = ", ".join(sorted(source_signal_names))
        raise ValueError(f"signal.csv contains multiple signal_name values: {names}. Specify --signal-name explicitly")

    selected = signal_frame.copy()
    selected_signal_name = signal_name
    if signal_name is not None:
        selected = selected.loc[selected["signal_name"].astype(str) == str(signal_name)].copy()
        if selected.empty:
            raise ValueError(f"signal.csv does not contain requested signal_name {signal_name!r}")
    elif len(source_signal_names) == 1:
        selected_signal_name = source_signal_names[0]
        selected = selected.loc[selected["signal_name"].astype(str) == selected_signal_name].copy()

    selected = selected.loc[selected["symbol"].astype(str) == str(symbol)].copy()
    if selected.empty:
        raise ValueError(f"No signal rows found for symbol {symbol!r}")

    selected["datetime"] = _normalize_daily_dates(selected["datetime"])
    selected["available_at"] = _normalize_daily_dates(selected["available_at"])
    selected["score"] = pd.to_numeric(selected["score"], errors="raise")
    selected["direction"] = pd.to_numeric(selected["direction"], errors="raise")
    selected["target_weight"] = pd.to_numeric(selected["target_weight"], errors="raise")
    selected = selected.sort_values(["datetime", "signal_name"], kind="mergesort").reset_index(drop=True)

    projected = selected.reindex(columns=V2_SIGNAL_COLUMNS).copy()
    nonzero_count = int((projected["target_weight"].astype(float).abs() > 0.0).sum())
    metadata = {
        "source_signal_row_count": int(len(signal_frame)),
        "selected_signal_row_count": int(len(projected)),
        "source_symbol_count": int(len(_unique_non_null_values(signal_frame["symbol"]))),
        "symbol": symbol,
        "signal_name": selected_signal_name,
        "nonzero_target_weight_count": nonzero_count,
        "all_flat_selected_symbol": nonzero_count == 0,
    }
    return projected, metadata


def validate_signal_market_alignment(projected_signal: pd.DataFrame, market_data: pd.DataFrame) -> dict[str, object]:
    signal_dates = pd.Index(_normalize_daily_dates(projected_signal["datetime"]).dropna().unique())
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


def _unique_non_null_values(series: pd.Series) -> list[str]:
    return sorted(series.dropna().astype(str).unique().tolist())


def main() -> None:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    derived_signal_dir = output_dir / "derived_signal"
    output_dir.mkdir(parents=True, exist_ok=True)
    derived_signal_dir.mkdir(parents=True, exist_ok=True)

    data_spec = DataSpec(path=args.market_data, symbol=args.symbol, datetime_column=args.datetime_column)
    signal_frame = load_signal_frame(args.signal_file)
    projected_signal, projection_metadata = project_single_symbol_signal(
        signal_frame,
        symbol=args.symbol,
        signal_name=args.signal_name,
    )
    market_data = load_market_data(data_spec)
    alignment_summary = validate_signal_market_alignment(projected_signal, market_data)

    warnings: list[str] = []
    if projection_metadata["all_flat_selected_symbol"]:
        warnings.append("Selected symbol is all-flat under this signal; demo validation may be uninformative.")
        print(ALL_FLAT_WARNING, file=sys.stderr)

    derived_signal_path = derived_signal_dir / DERIVED_SIGNAL_FILENAME
    projected_signal.to_csv(derived_signal_path, index=False)

    input_summary = {
        "stage": "ml_signal_single_symbol_projection_preflight",
        "source_signal_path": str(args.signal_file),
        "market_data_path": str(args.market_data),
        "derived_single_symbol_signal_path": str(derived_signal_path),
        "validation_mode": "single_symbol_projection",
        "date_alignment": alignment_summary,
        "warnings": warnings,
        **projection_metadata,
    }
    input_summary_path = output_dir / INPUT_SUMMARY_FILENAME
    write_json_artifact(input_summary_path, input_summary)

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
        output_dir=output_dir,
        experiment_name=args.experiment_name,
        signal_file=derived_signal_path,
        signal_name=args.signal_name,
    )
    execution = run_research_validation_protocol_with_details(research_config)
    receipt_payload = serialize_research_protocol_artifact_receipt(execution.artifact_receipt)
    research_summary_payload = serialize_research_protocol_summary(execution.research_protocol_summary)

    summary = {
        "status": "ok",
        "stage": "ml_signal_single_symbol_research_validation",
        "validation_mode": "single_symbol_projection",
        "source_signal_path": str(args.signal_file),
        "derived_single_symbol_signal_path": str(derived_signal_path),
        "market_data_path": str(args.market_data),
        "symbol": args.symbol,
        "signal_name": projection_metadata["signal_name"],
        "source_signal_row_count": projection_metadata["source_signal_row_count"],
        "selected_signal_row_count": projection_metadata["selected_signal_row_count"],
        "nonzero_target_weight_count": projection_metadata["nonzero_target_weight_count"],
        "all_flat_selected_symbol": projection_metadata["all_flat_selected_symbol"],
        "date_alignment": alignment_summary,
        "warnings": warnings,
        "does_train_model": False,
        "does_generate_predictions": False,
        "does_add_multi_symbol_backtest": False,
        "does_execute_live_trades": False,
        "boundary": (
            "Projects an already-generated cross-sectional ML signal to one symbol and validates it through "
            "the existing custom_signal research-validation protocol."
        ),
        "paths": {
            "input_summary": str(input_summary_path),
            "derived_single_symbol_signal": str(derived_signal_path),
            "research_validation_summary": None
            if receipt_payload is None
            else receipt_payload.get("research_protocol_summary_path"),
        },
        "research_validation_artifact_receipt": receipt_payload,
        "research_validation_summary": research_summary_payload,
    }
    summary_path = output_dir / SUMMARY_FILENAME
    write_json_artifact(summary_path, summary)

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
