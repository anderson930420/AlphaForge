from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from . import config
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
    validate_search.add_argument(
        "--permutation-null-model",
        type=str,
        default="return_block_reconstruction",
    )
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
    compare_strategies.add_argument(
        "--permutation-null-model",
        type=str,
        default="return_block_reconstruction",
    )
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
    research_validate.add_argument("--strategy", type=str, choices=STRATEGY_FAMILY_CHOICES, default="ma_crossover")
    research_validate.add_argument("--development-start", type=str, required=True)
    research_validate.add_argument("--development-end", type=str, required=True)
    research_validate.add_argument("--holdout-start", type=str, required=True)
    research_validate.add_argument("--holdout-end", type=str, required=True)
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
    research_validate.add_argument(
        "--permutation-null-model",
        type=str,
        default="return_block_reconstruction",
    )
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
    twse_search.add_argument("--holdout-cutoff-date", type=str, default=None)
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


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
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
            print(
                json.dumps(
                    _build_search_summary(
                        search_execution,
                        data_output=data_output,
                    ),
                    indent=2,
                    default=str,
                )
            )
            return

        data_spec = DataSpec(path=args.data, symbol=args.symbol)
        backtest_config = BacktestConfig(
            initial_capital=args.initial_capital,
            fee_rate=args.fee_rate,
            slippage_rate=args.slippage_rate,
            annualization_factor=args.annualization_factor,
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
            research_execution = run_research_validation_protocol_with_details(
                ResearchValidationConfig(
                    data_spec=data_spec,
                    strategy_name=args.strategy,
                    parameter_grid=_build_strategy_parameter_grid_from_args(args, parser),
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
        print(
            json.dumps(
                _build_search_summary(
                    search_execution,
                ),
                indent=2,
                default=str,
            )
        )
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


def _build_search_summary(
    search_execution,
    data_output: Path | None = None,
) -> dict:
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
