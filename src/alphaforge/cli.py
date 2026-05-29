from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

import pandas as pd

from . import config
from .open_asset_pricing import OAPQuantilePolicy, build_oap_v02_signal_frame
from .oap_mom12m_pipeline import run_oap_mom12m_pipeline_smoke
from .oap_multifactor import OAPMultiFactorConfig, build_multifactor_signal, load_feature_panel
from .signalforge_package import run_signalforge_v02_package_smoke
from .backtest import LEGACY_EXECUTION_SEMANTICS, SIGNED_EXECUTION_SEMANTICS, SUPPORTED_EXECUTION_SEMANTICS
from .experiment_runner import (
    run_experiment_with_artifacts,
    run_research_validation_protocol_with_details,
    run_search_with_details,
    run_strategy_comparison_with_details,
    run_validate_search_with_details,
    run_walk_forward_search_with_details,
)
from .policy_types import ParameterGrid
from .permutation import run_permutation_test_with_details
from .permutation import DEFAULT_PERMUTATION_TARGET_METRIC_NAME, SUPPORTED_PERMUTATION_TARGET_METRICS
from .report import render_experiment_report, save_experiment_report
from .artifact_report import render_artifact_report
from .schemas import (
    BacktestConfig,
    DataSpec,
    ResearchPeriod,
    ResearchValidationConfig,
    SearchSummary,
    StrategyComparisonConfig,
    StrategyFamilySearchConfig,
    StrategySpec,
    ValidationPermutationConfig,
    ValidationSplitConfig,
    WalkForwardConfig,
)
from .strategy_registry import supported_strategy_families
from .storage import (
    ensure_output_dir,
    serialize_artifact_receipt,
    serialize_experiment_result,
    serialize_permutation_test_artifact_receipt,
    serialize_permutation_test_summary,
    serialize_research_protocol_artifact_receipt,
    serialize_research_protocol_summary,
    serialize_strategy_comparison_artifact_receipt,
    serialize_strategy_comparison_summary,
    serialize_validation_artifact_receipt,
    serialize_validation_result,
    serialize_walk_forward_artifact_receipt,
    serialize_walk_forward_result,
    REPORT_FILENAME,
)

STRATEGY_FAMILY_CHOICES = supported_strategy_families()
RESEARCH_VALIDATION_STRATEGY_CHOICES = STRATEGY_FAMILY_CHOICES + ("custom_signal",)
DEFAULT_COMPARISON_STRATEGIES = list(STRATEGY_FAMILY_CHOICES)
DEFAULT_BREAKOUT_LOOKBACK_WINDOWS = [10, 20, 30, 40, 60]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AlphaForge workflow orchestration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("run", help="Run a single strategy experiment")
    _add_common_arguments(single)
    single.add_argument("--strategy", type=str, choices=STRATEGY_FAMILY_CHOICES, default="ma_crossover")
    single.add_argument("--short-window", type=int, default=None)
    single.add_argument("--long-window", type=int, default=None)
    single.add_argument("--lookback-window", type=int, default=None)
    single.add_argument("--generate-report", action="store_true")
    single.add_argument("--holdout-cutoff-date", type=str, default=None)

    search = subparsers.add_parser("search", help="Run grid search over a selected strategy family")
    _add_common_arguments(search)
    search.add_argument("--strategy", type=str, choices=STRATEGY_FAMILY_CHOICES, default="ma_crossover")
    search.add_argument("--short-windows", type=int, nargs="+", default=config.SHORT_WINDOW_RANGE)
    search.add_argument("--long-windows", type=int, nargs="+", default=config.LONG_WINDOW_RANGE)
    search.add_argument("--lookback-windows", type=int, nargs="+", default=None)
    search.add_argument("--max-drawdown-cap", type=float, default=None)
    search.add_argument("--min-trade-count", type=int, default=None)
    search.add_argument("--generate-report", action="store_true")
    search.add_argument("--holdout-cutoff-date", type=str, default=None)

    validate_search = subparsers.add_parser("validate-search", help="Run train/test validation for a selected strategy family")
    _add_common_arguments(validate_search)
    validate_search.add_argument("--strategy", type=str, choices=STRATEGY_FAMILY_CHOICES, default="ma_crossover")
    validate_search.add_argument("--short-windows", type=int, nargs="+", default=config.SHORT_WINDOW_RANGE)
    validate_search.add_argument("--long-windows", type=int, nargs="+", default=config.LONG_WINDOW_RANGE)
    validate_search.add_argument("--lookback-windows", type=int, nargs="+", default=None)
    validate_search.add_argument("--split-ratio", type=float, required=True)
    validate_search.add_argument("--max-drawdown-cap", type=float, default=None)
    validate_search.add_argument("--min-trade-count", type=int, default=None)
    validate_search.add_argument("--holdout-cutoff-date", type=str, default=None)
    validate_search.add_argument("--permutation-test", action="store_true")
    validate_search.add_argument("--permutations", type=int, default=25)
    validate_search.add_argument("--permutation-seed", type=int, default=42)
    validate_search.add_argument("--permutation-block-size", type=int, default=2)
    validate_search.add_argument("--permutation-null-model", type=str, default="return_block_reconstruction")
    validate_search.add_argument("--permutation-scope", type=str, default="test")

    compare_strategies = subparsers.add_parser(
        "compare-strategies",
        help="Compare multiple strategy families through one validation protocol",
    )
    _add_common_arguments(compare_strategies)
    compare_strategies.add_argument("--split-ratio", type=float, required=True)
    compare_strategies.add_argument("--strategies", type=str, nargs="+", choices=STRATEGY_FAMILY_CHOICES, default=None)
    compare_strategies.add_argument("--short-windows", type=int, nargs="+", default=config.SHORT_WINDOW_RANGE)
    compare_strategies.add_argument("--long-windows", type=int, nargs="+", default=config.LONG_WINDOW_RANGE)
    compare_strategies.add_argument("--lookback-windows", type=int, nargs="+", default=DEFAULT_BREAKOUT_LOOKBACK_WINDOWS)
    compare_strategies.add_argument("--max-drawdown-cap", type=float, default=None)
    compare_strategies.add_argument("--min-trade-count", type=int, default=None)
    compare_strategies.add_argument("--holdout-cutoff-date", type=str, default=None)
    compare_strategies.add_argument("--permutation-test", action="store_true")
    compare_strategies.add_argument("--permutations", type=int, default=25)
    compare_strategies.add_argument("--permutation-seed", type=int, default=42)
    compare_strategies.add_argument("--permutation-block-size", type=int, default=2)
    compare_strategies.add_argument("--permutation-null-model", type=str, default="return_block_reconstruction")
    compare_strategies.add_argument("--permutation-scope", type=str, default="test")

    walk_forward = subparsers.add_parser("walk-forward", help="Run walk-forward validation for a selected strategy family")
    _add_common_arguments(walk_forward)
    walk_forward.add_argument("--strategy", type=str, choices=STRATEGY_FAMILY_CHOICES, default="ma_crossover")
    walk_forward.add_argument("--short-windows", type=int, nargs="+", default=config.SHORT_WINDOW_RANGE)
    walk_forward.add_argument("--long-windows", type=int, nargs="+", default=config.LONG_WINDOW_RANGE)
    walk_forward.add_argument("--lookback-windows", type=int, nargs="+", default=None)
    walk_forward.add_argument("--train-size", type=int, required=True)
    walk_forward.add_argument("--test-size", type=int, required=True)
    walk_forward.add_argument("--step-size", type=int, required=True)
    walk_forward.add_argument("--max-drawdown-cap", type=float, default=None)
    walk_forward.add_argument("--min-trade-count", type=int, default=None)
    walk_forward.add_argument("--holdout-cutoff-date", type=str, default=None)

    research_validate = subparsers.add_parser(
        "research-validate",
        help="Run development/holdout research validation with a frozen final holdout candidate",
    )
    _add_common_arguments(research_validate)
    research_validate.add_argument("--strategy", type=str, choices=RESEARCH_VALIDATION_STRATEGY_CHOICES, default="ma_crossover")
    research_validate.add_argument("--development-start", type=str, required=True)
    research_validate.add_argument("--development-end", type=str, required=True)
    research_validate.add_argument("--holdout-start", type=str, required=True)
    research_validate.add_argument("--holdout-end", type=str, required=True)
    research_validate.add_argument("--signal-file", "--signal-path", dest="signal_file", type=Path, default=None)
    research_validate.add_argument("--signal-name", type=str, default=None)
    research_validate.add_argument("--short-windows", type=int, nargs="+", default=config.SHORT_WINDOW_RANGE)
    research_validate.add_argument("--long-windows", type=int, nargs="+", default=config.LONG_WINDOW_RANGE)
    research_validate.add_argument("--lookback-windows", type=int, nargs="+", default=None)
    research_validate.add_argument("--train-size", type=int, required=True)
    research_validate.add_argument("--test-size", type=int, required=True)
    research_validate.add_argument("--step-size", type=int, required=True)
    research_validate.add_argument("--max-drawdown-cap", type=float, default=None)
    research_validate.add_argument("--min-trade-count", type=int, default=None)
    research_validate.add_argument("--permutations", type=int, default=0)
    research_validate.add_argument("--seed", type=int, default=42)
    research_validate.add_argument("--block-size", type=int, default=2)
    research_validate.add_argument("--permutation-null-model", type=str, default="return_block_reconstruction")
    research_validate.add_argument("--permutation-scope", type=str, default="development")

    permutation_test = subparsers.add_parser(
        "permutation-test",
        help="Run a permutation/null-comparison diagnostic for a fixed strategy candidate",
    )
    _add_common_arguments(permutation_test)
    permutation_test.add_argument("--strategy", type=str, choices=STRATEGY_FAMILY_CHOICES, default="ma_crossover")
    permutation_test.add_argument("--short-window", type=int, default=None)
    permutation_test.add_argument("--long-window", type=int, default=None)
    permutation_test.add_argument("--lookback-window", type=int, default=None)
    permutation_test.add_argument("--permutations", type=int, required=True)
    permutation_test.add_argument("--block-size", type=int, required=True)
    permutation_test.add_argument(
        "--target-metric",
        type=str,
        choices=SUPPORTED_PERMUTATION_TARGET_METRICS,
        default=DEFAULT_PERMUTATION_TARGET_METRIC_NAME,
    )
    permutation_test.add_argument("--seed", type=int, default=42)
    permutation_test.add_argument("--holdout-cutoff-date", type=str, default=None)

    fetch_twse = subparsers.add_parser("fetch-twse", help="Fetch TWSE stock-day data and save standardized CSV")
    fetch_twse.add_argument("--stock-no", type=str, required=True)
    fetch_twse.add_argument("--start-month", type=str, required=True, help="YYYY-MM")
    fetch_twse.add_argument("--end-month", type=str, required=True, help="YYYY-MM")
    fetch_twse.add_argument("--output", type=Path, required=True)

    twse_search = subparsers.add_parser("twse-search", help="Fetch TWSE stock-day data, save CSV, and run MA search")
    twse_search.add_argument("--stock-no", type=str, required=True)
    twse_search.add_argument("--start-month", type=str, required=True, help="YYYY-MM")
    twse_search.add_argument("--end-month", type=str, required=True, help="YYYY-MM")
    twse_search.add_argument("--data-output", type=Path, required=True)
    twse_search.add_argument("--output-dir", type=Path, default=config.OUTPUT_DIR)
    twse_search.add_argument("--experiment-name", type=str, default="twse_search")
    twse_search.add_argument("--short-windows", type=int, nargs="+", default=config.SHORT_WINDOW_RANGE)
    twse_search.add_argument("--long-windows", type=int, nargs="+", default=config.LONG_WINDOW_RANGE)
    twse_search.add_argument("--max-drawdown-cap", type=float, default=None)
    twse_search.add_argument("--min-trade-count", type=int, default=None)
    twse_search.add_argument("--generate-report", action="store_true")
    twse_search.add_argument("--initial-capital", type=float, default=config.INITIAL_CAPITAL)
    twse_search.add_argument("--fee-rate", type=float, default=config.DEFAULT_FEE_RATE)
    twse_search.add_argument("--slippage-rate", type=float, default=config.DEFAULT_SLIPPAGE_RATE)
    twse_search.add_argument("--annualization-factor", type=int, default=config.DEFAULT_ANNUALIZATION)
    twse_search.add_argument(
        "--execution-semantics",
        type=str,
        choices=SUPPORTED_EXECUTION_SEMANTICS,
        default=LEGACY_EXECUTION_SEMANTICS,
    )
    twse_search.add_argument("--holdout-cutoff-date", type=str, default=None)

    build_oap_signal = subparsers.add_parser(
        "build-oap-signal",
        help="Build AlphaForge v0.2 signal.csv from an Open Asset Pricing-style characteristic CSV",
    )
    build_oap_signal.add_argument("--input", required=True, type=Path)
    build_oap_signal.add_argument("--output", required=True, type=Path)
    build_oap_signal.add_argument("--characteristic", required=True)
    build_oap_signal.add_argument("--date-col", default="date")
    build_oap_signal.add_argument("--asset-id-col", default="asset_id")
    build_oap_signal.add_argument("--available-at-col", default=None)
    build_oap_signal.add_argument("--signal-name", default=None)
    build_oap_signal.add_argument("--source", default="OpenAssetPricing")
    build_oap_signal.add_argument("--long-quantile", type=float, default=0.8)
    build_oap_signal.add_argument("--short-quantile", type=float, default=0.2)
    build_oap_signal.add_argument("--gross-long-weight", type=float, default=1.0)
    build_oap_signal.add_argument("--gross-short-weight", type=float, default=-1.0)
    build_oap_signal.add_argument("--invert-score", action="store_true")

    build_oap_multifactor = subparsers.add_parser(
        "build-oap-multifactor-signal",
        help="Build AlphaForge v0.2 signal.csv from a local OAP multi-factor feature panel",
    )
    build_oap_multifactor.add_argument("--features", required=True, type=Path)
    build_oap_multifactor.add_argument("--config", required=True, type=Path)
    build_oap_multifactor.add_argument("--output", required=True, type=Path)
    build_oap_multifactor.add_argument("--source", default="OpenAssetPricing")

    run_oap_mom12m = subparsers.add_parser(
        "run-oap-mom12m-pipeline",
        help="Run the local OAP / JKP Mom12m pipeline smoke through AlphaForge",
    )
    run_oap_mom12m.add_argument("--characteristics", required=True, type=Path)
    run_oap_mom12m.add_argument("--contract", required=True, type=Path)
    run_oap_mom12m.add_argument("--market-data", required=True, type=Path)
    run_oap_mom12m.add_argument("--signal-output", required=True, type=Path)
    run_oap_mom12m.add_argument("--symbol", type=str, default=None)
    run_oap_mom12m.add_argument("--initial-capital", type=float, default=config.INITIAL_CAPITAL)
    run_oap_mom12m.add_argument("--fee-rate", type=float, default=config.DEFAULT_FEE_RATE)
    run_oap_mom12m.add_argument("--slippage-rate", type=float, default=config.DEFAULT_SLIPPAGE_RATE)
    run_oap_mom12m.add_argument("--annualization-factor", type=int, default=config.DEFAULT_ANNUALIZATION)

    smoke_signalforge_package = subparsers.add_parser(
        "smoke-signalforge-package",
        help="Validate and smoke-test a SignalForge v0.2 package through AlphaForge custom_signal",
    )
    smoke_signalforge_package.add_argument("--package", required=True, type=Path)
    smoke_signalforge_package.add_argument("--initial-capital", type=float, default=config.INITIAL_CAPITAL)
    smoke_signalforge_package.add_argument("--fee-rate", type=float, default=config.DEFAULT_FEE_RATE)
    smoke_signalforge_package.add_argument("--slippage-rate", type=float, default=config.DEFAULT_SLIPPAGE_RATE)
    smoke_signalforge_package.add_argument("--annualization-factor", type=int, default=config.DEFAULT_ANNUALIZATION)

    render_artifact_report_parser = subparsers.add_parser(
        "render-artifact-report",
        help="Render a standalone HTML report from AlphaForge artifact files",
    )
    render_artifact_report_parser.add_argument("--artifact-dir", required=True, type=Path)
    render_artifact_report_parser.add_argument("--output", type=Path, default=None)
    render_artifact_report_parser.add_argument("--report-json", type=Path, default=None)

    return parser


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data", type=Path, required=True, help="Path to OHLCV CSV")
    parser.add_argument("--symbol", type=str, default="UNKNOWN")
    parser.add_argument("--output-dir", type=Path, default=config.OUTPUT_DIR)
    parser.add_argument("--experiment-name", type=str, default="alphaforge_run")
    parser.add_argument("--initial-capital", type=float, default=config.INITIAL_CAPITAL)
    parser.add_argument("--fee-rate", type=float, default=config.DEFAULT_FEE_RATE)
    parser.add_argument("--slippage-rate", type=float, default=config.DEFAULT_SLIPPAGE_RATE)
    parser.add_argument("--annualization-factor", type=int, default=config.DEFAULT_ANNUALIZATION)
    parser.add_argument(
        "--execution-semantics",
        type=str,
        choices=SUPPORTED_EXECUTION_SEMANTICS,
        default=LEGACY_EXECUTION_SEMANTICS,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "run-oap-mom12m-pipeline":
            market_data = pd.read_csv(args.market_data)
            pipeline_config = BacktestConfig(
                initial_capital=args.initial_capital,
                fee_rate=args.fee_rate,
                slippage_rate=args.slippage_rate,
                annualization_factor=args.annualization_factor,
                execution_semantics=SIGNED_EXECUTION_SEMANTICS,
            )
            result = run_oap_mom12m_pipeline_smoke(
                characteristics_path=args.characteristics,
                contract_path=args.contract,
                market_data=market_data,
                signal_output_path=args.signal_output,
                symbol=args.symbol,
                backtest_config=pipeline_config,
            )
            summary = {
                "status": "passed",
                "characteristics": str(args.characteristics),
                "contract": str(args.contract),
                "market_data": str(args.market_data),
                "signal_output": str(result.signal_output_path),
                "factor_rows": int(len(result.factor_frame)),
                "signal_rows": int(len(result.signal_frame)),
                "signal_contract_version": result.signal_metadata.get("signal_contract_version"),
                "target_position_source_column": result.signal_metadata.get("target_position_source_column"),
                "execution_semantics": SIGNED_EXECUTION_SEMANTICS,
                "equity_curve_rows": int(len(result.equity_curve)),
                "trade_count": int(len(result.trades)),
                "final_equity": float(result.equity_curve["equity"].iloc[-1]),
            }
            if args.symbol is not None:
                summary["symbol"] = args.symbol
            print(json.dumps(summary, indent=2, sort_keys=True))
            return

        if args.command == "smoke-signalforge-package":
            smoke_config = BacktestConfig(
                initial_capital=args.initial_capital,
                fee_rate=args.fee_rate,
                slippage_rate=args.slippage_rate,
                annualization_factor=args.annualization_factor,
                execution_semantics="signed_close_to_close_lagged",
            )
            result = run_signalforge_v02_package_smoke(
                args.package,
                backtest_config=smoke_config,
            )
            summary = {
                "status": "passed",
                "package": str(result.package_dir),
                "market_data_row_count": result.market_data_row_count,
                "signal_row_count": result.signal_row_count,
                "signal_contract_version": result.signal_metadata.get("signal_contract_version"),
                "target_position_source_column": result.signal_metadata.get("target_position_source_column"),
                "execution_semantics": "signed_close_to_close_lagged",
                "equity_curve_rows": int(len(result.equity_curve)),
                "trade_count": int(len(result.trades)),
                "final_equity": float(result.equity_curve["equity"].iloc[-1]),
            }
            print(json.dumps(summary, indent=2, sort_keys=True))
            return

        if args.command == "render-artifact-report":
            output_path = render_artifact_report(
                artifact_dir=args.artifact_dir,
                output_path=args.output,
                report_json_path=args.report_json,
            )
            print(json.dumps({"status": "ok", "report_path": str(output_path)}, indent=2))
            return

        if args.command == "build-oap-signal":
            characteristics = pd.read_csv(args.input)
            policy = OAPQuantilePolicy(
                long_quantile=args.long_quantile,
                short_quantile=args.short_quantile,
                gross_long_weight=args.gross_long_weight,
                gross_short_weight=args.gross_short_weight,
            )
            signal_frame = build_oap_v02_signal_frame(
                characteristics,
                characteristic=args.characteristic,
                date_col=args.date_col,
                asset_id_col=args.asset_id_col,
                available_at_col=args.available_at_col,
                signal_name=args.signal_name,
                source=args.source,
                policy=policy,
                invert_score=args.invert_score,
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            signal_frame.to_csv(args.output, index=False)
            print(f"Wrote {len(signal_frame)} v0.2 signal rows to {args.output}")
            return

        if args.command == "build-oap-multifactor-signal":
            mf_config = OAPMultiFactorConfig.from_yaml(args.config)
            features_df = load_feature_panel(args.features, date_col=mf_config.date_col, asset_id_col=mf_config.asset_id_col)
            signal_frame = build_multifactor_signal(features_df, mf_config, source=args.source)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            signal_frame.to_csv(args.output, index=False)
            print(f"Wrote {len(signal_frame)} v0.2 signal rows to {args.output}")
            return

        if args.command == "fetch-twse":
            TwseFetchRequest, fetch_stock_day_history, save_stock_day_history = _load_twse_client()
            frame = fetch_stock_day_history(
                TwseFetchRequest(
                    stock_no=args.stock_no,
                    start_month=args.start_month,
                    end_month=args.end_month,
                )
            )
            output_path = save_stock_day_history(frame, args.output)
            print(json.dumps({"rows": len(frame), "output": str(output_path)}, indent=2))
            return

        if args.command == "twse-search":
            TwseFetchRequest, fetch_stock_day_history, save_stock_day_history = _load_twse_client()
            frame = fetch_stock_day_history(
                TwseFetchRequest(
                    stock_no=args.stock_no,
                    start_month=args.start_month,
                    end_month=args.end_month,
                )
            )
            data_output = save_stock_day_history(frame, args.data_output)
            data_spec = DataSpec(path=data_output, symbol=args.stock_no)
            backtest_config = BacktestConfig(
                initial_capital=args.initial_capital,
                fee_rate=args.fee_rate,
                slippage_rate=args.slippage_rate,
                annualization_factor=args.annualization_factor,
                execution_semantics=args.execution_semantics,
            )
            search_execution = run_search_with_details(
                data_spec=data_spec,
                parameter_grid={
                    "short_window": args.short_windows,
                    "long_window": args.long_windows,
                },
                strategy_name="ma_crossover",
                backtest_config=backtest_config,
                output_dir=args.output_dir,
                experiment_name=args.experiment_name,
                max_drawdown_cap=args.max_drawdown_cap,
                min_trade_count=args.min_trade_count,
                generate_best_report=args.generate_report,
                holdout_cutoff_date=args.holdout_cutoff_date,
            )
            print(json.dumps(_build_search_summary(search_execution, data_output=data_output), indent=2, default=str))
            return

        data_spec = DataSpec(path=args.data, symbol=args.symbol)
        backtest_config = BacktestConfig(
            initial_capital=args.initial_capital,
            fee_rate=args.fee_rate,
            slippage_rate=args.slippage_rate,
            annualization_factor=args.annualization_factor,
            execution_semantics=args.execution_semantics,
        )

        if args.command == "run":
            strategy_spec = _build_strategy_spec_from_args(args, parser)
            execution = run_experiment_with_artifacts(
                data_spec=data_spec,
                strategy_spec=strategy_spec,
                backtest_config=backtest_config,
                output_dir=args.output_dir,
                experiment_name=args.experiment_name,
                holdout_cutoff_date=args.holdout_cutoff_date,
            )
            payload = serialize_experiment_result(execution.result)
            payload["artifacts"] = serialize_artifact_receipt(execution.artifact_receipt)
            if args.generate_report:
                experiment_dir = ensure_output_dir(args.output_dir / args.experiment_name)
                report_content = render_experiment_report(execution.report_input)
                report_path = save_experiment_report(report_content, experiment_dir / REPORT_FILENAME)
                payload["report_path"] = str(report_path)
            print(json.dumps(payload, indent=2, default=str))
            return

        if args.command == "validate-search":
            validation_execution = run_validate_search_with_details(
                data_spec=data_spec,
                parameter_grid=_build_strategy_parameter_grid_from_args(args, parser),
                split_ratio=args.split_ratio,
                strategy_name=args.strategy,
                backtest_config=backtest_config,
                output_dir=args.output_dir,
                experiment_name=args.experiment_name,
                max_drawdown_cap=args.max_drawdown_cap,
                min_trade_count=args.min_trade_count,
                holdout_cutoff_date=args.holdout_cutoff_date,
                permutation_config=_build_validation_permutation_config_from_args(args),
            )
            payload = serialize_validation_result(validation_execution.validation_result)
            payload.update(serialize_validation_artifact_receipt(validation_execution.artifact_receipt) or {})
            print(json.dumps(payload, indent=2, default=str))
            return

        if args.command == "compare-strategies":
            comparison_execution = run_strategy_comparison_with_details(
                StrategyComparisonConfig(
                    data_spec=data_spec,
                    split_config=ValidationSplitConfig(split_ratio=args.split_ratio),
                    backtest_config=backtest_config,
                    strategy_families=_build_strategy_family_search_configs_from_args(args),
                    permutation_config=_build_validation_permutation_config_from_args(args),
                    max_drawdown_cap=args.max_drawdown_cap,
                    min_trade_count=args.min_trade_count,
                    holdout_cutoff_date=args.holdout_cutoff_date,
                    output_dir=args.output_dir,
                    experiment_name=args.experiment_name,
                )
            )
            payload = serialize_strategy_comparison_summary(comparison_execution.comparison_summary)
            payload.update(serialize_strategy_comparison_artifact_receipt(comparison_execution.artifact_receipt) or {})
            print(json.dumps(payload, indent=2, default=str))
            return

        if args.command == "walk-forward":
            walk_forward_execution = run_walk_forward_search_with_details(
                data_spec=data_spec,
                parameter_grid=_build_strategy_parameter_grid_from_args(args, parser),
                train_size=args.train_size,
                test_size=args.test_size,
                step_size=args.step_size,
                strategy_name=args.strategy,
                backtest_config=backtest_config,
                output_dir=args.output_dir,
                experiment_name=args.experiment_name,
                max_drawdown_cap=args.max_drawdown_cap,
                min_trade_count=args.min_trade_count,
                holdout_cutoff_date=args.holdout_cutoff_date,
            )
            payload = serialize_walk_forward_result(walk_forward_execution.walk_forward_result)
            payload.update(serialize_walk_forward_artifact_receipt(walk_forward_execution.artifact_receipt) or {})
            print(json.dumps(payload, indent=2, default=str))
            return

        if args.command == "research-validate":
            if args.strategy == "custom_signal":
                if args.signal_file is None:
                    parser.error("--signal-file is required when --strategy custom_signal")
                parameter_grid = {}
            else:
                if args.signal_file is not None or args.signal_name is not None:
                    parser.error("--signal-file and --signal-name may only be used with --strategy custom_signal")
                parameter_grid = _build_strategy_parameter_grid_from_args(args, parser)
            research_execution = run_research_validation_protocol_with_details(
                ResearchValidationConfig(
                    data_spec=data_spec,
                    strategy_name=args.strategy,
                    parameter_grid=parameter_grid,
                    development_period=ResearchPeriod(start=args.development_start, end=args.development_end),
                    holdout_period=ResearchPeriod(start=args.holdout_start, end=args.holdout_end),
                    walk_forward_config=WalkForwardConfig(
                        train_size=args.train_size,
                        test_size=args.test_size,
                        step_size=args.step_size,
                    ),
                    backtest_config=backtest_config,
                    permutation_config=_build_research_validation_permutation_config_from_args(args),
                    max_drawdown_cap=args.max_drawdown_cap,
                    min_trade_count=args.min_trade_count,
                    output_dir=args.output_dir,
                    experiment_name=args.experiment_name,
                    signal_file=args.signal_file,
                    signal_name=args.signal_name,
                )
            )
            payload = serialize_research_protocol_summary(research_execution.research_protocol_summary)
            payload.update(serialize_research_protocol_artifact_receipt(research_execution.artifact_receipt) or {})
            print(json.dumps(payload, indent=2, default=str))
            return

        if args.command == "permutation-test":
            permutation_execution = run_permutation_test_with_details(
                data_spec=data_spec,
                strategy_spec=_build_permutation_strategy_spec_from_args(args, parser),
                permutation_count=args.permutations,
                block_size=args.block_size,
                target_metric_name=args.target_metric,
                seed=args.seed,
                backtest_config=backtest_config,
                output_dir=args.output_dir,
                experiment_name=args.experiment_name,
                holdout_cutoff_date=args.holdout_cutoff_date,
            )
            payload = serialize_permutation_test_summary(permutation_execution.permutation_test_summary)
            payload.update(serialize_permutation_test_artifact_receipt(permutation_execution.artifact_receipt) or {})
            print(json.dumps(payload, indent=2, default=str))
            return

        search_execution = run_search_with_details(
            data_spec=data_spec,
            parameter_grid=_build_strategy_parameter_grid_from_args(args, parser),
            strategy_name=args.strategy,
            backtest_config=backtest_config,
            output_dir=args.output_dir,
            experiment_name=args.experiment_name,
            max_drawdown_cap=args.max_drawdown_cap,
            min_trade_count=args.min_trade_count,
            generate_best_report=args.generate_report,
            holdout_cutoff_date=args.holdout_cutoff_date,
        )
        print(json.dumps(_build_search_summary(search_execution), indent=2, default=str))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def _load_twse_client():
    module = importlib.import_module("alphaforge.twse_client")
    return module.TwseFetchRequest, module.fetch_stock_day_history, module.save_stock_day_history


def _build_strategy_spec_from_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> StrategySpec:
    if args.strategy == "ma_crossover":
        if args.short_window is None or args.long_window is None:
            parser.error("MA crossover run requires --short-window and --long-window")
        return StrategySpec(
            name="ma_crossover",
            parameters={"short_window": args.short_window, "long_window": args.long_window},
        )
    if args.strategy == "breakout":
        if args.lookback_window is None:
            parser.error("Breakout run requires --lookback-window")
        return StrategySpec(name="breakout", parameters={"lookback_window": args.lookback_window})
    parser.error(f"Unsupported strategy: {args.strategy}")


def _build_strategy_parameter_grid_from_args(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> ParameterGrid:
    if args.strategy == "ma_crossover":
        return {
            "short_window": args.short_windows,
            "long_window": args.long_windows,
        }
    if args.strategy == "breakout":
        if args.lookback_windows is None:
            parser.error("Breakout search requires --lookback-windows")
        return {"lookback_window": args.lookback_windows}
    parser.error(f"Unsupported strategy: {args.strategy}")


def _build_permutation_strategy_spec_from_args(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> StrategySpec:
    if args.strategy == "ma_crossover":
        if args.short_window is None or args.long_window is None:
            parser.error("MA crossover permutation-test requires --short-window and --long-window")
        return StrategySpec(
            name="ma_crossover",
            parameters={"short_window": args.short_window, "long_window": args.long_window},
        )
    if args.strategy == "breakout":
        if args.lookback_window is None:
            parser.error("Breakout permutation-test requires --lookback-window")
        return StrategySpec(name="breakout", parameters={"lookback_window": args.lookback_window})
    parser.error(f"Unsupported strategy: {args.strategy}")


def _build_validation_permutation_config_from_args(args: argparse.Namespace) -> ValidationPermutationConfig | None:
    if not args.permutation_test:
        return None
    return ValidationPermutationConfig(
        enabled=True,
        permutations=args.permutations,
        seed=args.permutation_seed,
        block_size=args.permutation_block_size,
        null_model=args.permutation_null_model,
        scope=args.permutation_scope,
    )


def _build_research_validation_permutation_config_from_args(args: argparse.Namespace) -> ValidationPermutationConfig | None:
    if args.permutations <= 0:
        return None
    return ValidationPermutationConfig(
        enabled=True,
        permutations=args.permutations,
        seed=args.seed,
        block_size=args.block_size,
        null_model=args.permutation_null_model,
        scope=args.permutation_scope,
    )


def _build_strategy_family_search_configs_from_args(args: argparse.Namespace) -> list[StrategyFamilySearchConfig]:
    requested_strategies = list(args.strategies or DEFAULT_COMPARISON_STRATEGIES)
    configs: list[StrategyFamilySearchConfig] = []
    for strategy_name in requested_strategies:
        if strategy_name == "ma_crossover":
            configs.append(
                StrategyFamilySearchConfig(
                    strategy_name="ma_crossover",
                    parameter_grid={
                        "short_window": args.short_windows,
                        "long_window": args.long_windows,
                    },
                )
            )
            continue
        if strategy_name == "breakout":
            configs.append(
                StrategyFamilySearchConfig(
                    strategy_name="breakout",
                    parameter_grid={"lookback_window": args.lookback_windows},
                )
            )
            continue
        raise ValueError(f"Unsupported strategy: {strategy_name}")
    return configs


def _build_search_summary(search_execution, data_output: Path | None = None) -> dict:
    payload = _serialize_search_summary(search_execution.summary)
    if data_output is not None:
        payload["data_output"] = str(data_output)
    receipt = search_execution.artifact_receipt
    if receipt is not None:
        if receipt.ranked_results_path is not None:
            payload["ranked_results_path"] = str(receipt.ranked_results_path)
        if receipt.best_report_path is not None:
            payload["report_path"] = str(receipt.best_report_path)
        if receipt.comparison_report_path is not None:
            payload["search_report_path"] = str(receipt.comparison_report_path)
    return payload


def _serialize_search_summary(summary: SearchSummary) -> dict:
    return {
        "strategy_name": summary.strategy_name,
        "search_parameter_names": summary.search_parameter_names,
        "attempted_combinations": summary.attempted_combinations,
        "valid_combinations": summary.valid_combinations,
        "invalid_combinations": summary.invalid_combinations,
        "result_count": summary.result_count,
        "ranking_score": summary.ranking_score,
        "best_result": serialize_experiment_result(summary.best_result) if summary.best_result is not None else None,
        "top_results": [serialize_experiment_result(result) for result in summary.top_results],
    }


if __name__ == "__main__":
    main()
