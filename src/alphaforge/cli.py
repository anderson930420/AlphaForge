from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from . import config
from .experiment_runner import (
    run_experiment_with_artifacts,
    run_search_with_details,
    run_validate_search_with_details,
    run_walk_forward_search_with_details,
)
from .permutation import run_permutation_test_with_details
from .report import render_experiment_report, save_experiment_report
from .schemas import BacktestConfig, DataSpec, SearchSummary, StrategySpec
from .storage import (
    ensure_output_dir,
    serialize_artifact_receipt,
    serialize_experiment_result,
    serialize_permutation_test_artifact_receipt,
    serialize_permutation_test_summary,
    serialize_validation_artifact_receipt,
    serialize_validation_result,
    serialize_walk_forward_artifact_receipt,
    serialize_walk_forward_result,
    REPORT_FILENAME,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AlphaForge workflow orchestration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("run", help="Run a single MA crossover experiment")
    _add_common_arguments(single)
    single.add_argument("--short-window", type=int, required=True)
    single.add_argument("--long-window", type=int, required=True)
    single.add_argument("--generate-report", action="store_true")

    search = subparsers.add_parser("search", help="Run grid search over MA windows")
    _add_common_arguments(search)
    search.add_argument("--short-windows", type=int, nargs="+", default=config.SHORT_WINDOW_RANGE)
    search.add_argument("--long-windows", type=int, nargs="+", default=config.LONG_WINDOW_RANGE)
    search.add_argument("--max-drawdown-cap", type=float, default=None)
    search.add_argument("--min-trade-count", type=int, default=None)
    search.add_argument("--generate-report", action="store_true")

    validate_search = subparsers.add_parser("validate-search", help="Run train/test validation for MA parameter search")
    _add_common_arguments(validate_search)
    validate_search.add_argument("--short-windows", type=int, nargs="+", default=config.SHORT_WINDOW_RANGE)
    validate_search.add_argument("--long-windows", type=int, nargs="+", default=config.LONG_WINDOW_RANGE)
    validate_search.add_argument("--split-ratio", type=float, required=True)
    validate_search.add_argument("--max-drawdown-cap", type=float, default=None)
    validate_search.add_argument("--min-trade-count", type=int, default=None)

    walk_forward = subparsers.add_parser("walk-forward", help="Run walk-forward validation for MA parameter search")
    _add_common_arguments(walk_forward)
    walk_forward.add_argument("--short-windows", type=int, nargs="+", default=config.SHORT_WINDOW_RANGE)
    walk_forward.add_argument("--long-windows", type=int, nargs="+", default=config.LONG_WINDOW_RANGE)
    walk_forward.add_argument("--train-size", type=int, required=True)
    walk_forward.add_argument("--test-size", type=int, required=True)
    walk_forward.add_argument("--step-size", type=int, required=True)
    walk_forward.add_argument("--max-drawdown-cap", type=float, default=None)
    walk_forward.add_argument("--min-trade-count", type=int, default=None)

    permutation_test = subparsers.add_parser(
        "permutation-test",
        help="Run a permutation/null-comparison diagnostic for a fixed MA candidate",
    )
    _add_common_arguments(permutation_test)
    permutation_test.add_argument("--short-window", type=int, required=True)
    permutation_test.add_argument("--long-window", type=int, required=True)
    permutation_test.add_argument("--permutations", type=int, required=True)
    permutation_test.add_argument("--seed", type=int, default=42)

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
    args = build_parser().parse_args()

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
                backtest_config=backtest_config,
                output_dir=args.output_dir,
                experiment_name=args.experiment_name,
                max_drawdown_cap=args.max_drawdown_cap,
                min_trade_count=args.min_trade_count,
                generate_best_report=args.generate_report,
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
            strategy_spec = StrategySpec(
                name="ma_crossover",
                parameters={"short_window": args.short_window, "long_window": args.long_window},
            )
            execution = run_experiment_with_artifacts(
                data_spec=data_spec,
                strategy_spec=strategy_spec,
                backtest_config=backtest_config,
                output_dir=args.output_dir,
                experiment_name=args.experiment_name,
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
                parameter_grid={
                    "short_window": args.short_windows,
                    "long_window": args.long_windows,
                },
                split_ratio=args.split_ratio,
                backtest_config=backtest_config,
                output_dir=args.output_dir,
                experiment_name=args.experiment_name,
                max_drawdown_cap=args.max_drawdown_cap,
                min_trade_count=args.min_trade_count,
            )
            payload = serialize_validation_result(validation_execution.validation_result)
            payload.update(serialize_validation_artifact_receipt(validation_execution.artifact_receipt) or {})
            print(json.dumps(payload, indent=2, default=str))
            return

        if args.command == "walk-forward":
            walk_forward_execution = run_walk_forward_search_with_details(
                data_spec=data_spec,
                parameter_grid={
                    "short_window": args.short_windows,
                    "long_window": args.long_windows,
                },
                train_size=args.train_size,
                test_size=args.test_size,
                step_size=args.step_size,
                backtest_config=backtest_config,
                output_dir=args.output_dir,
                experiment_name=args.experiment_name,
                max_drawdown_cap=args.max_drawdown_cap,
                min_trade_count=args.min_trade_count,
            )
            payload = serialize_walk_forward_result(walk_forward_execution.walk_forward_result)
            payload.update(serialize_walk_forward_artifact_receipt(walk_forward_execution.artifact_receipt) or {})
            print(json.dumps(payload, indent=2, default=str))
            return

        if args.command == "permutation-test":
            permutation_execution = run_permutation_test_with_details(
                data_spec=data_spec,
                strategy_spec=StrategySpec(
                    name="ma_crossover",
                    parameters={"short_window": args.short_window, "long_window": args.long_window},
                ),
                permutation_count=args.permutations,
                seed=args.seed,
                backtest_config=backtest_config,
                output_dir=args.output_dir,
                experiment_name=args.experiment_name,
            )
            payload = serialize_permutation_test_summary(permutation_execution.permutation_test_summary)
            payload.update(serialize_permutation_test_artifact_receipt(permutation_execution.artifact_receipt) or {})
            print(json.dumps(payload, indent=2, default=str))
            return

        search_execution = run_search_with_details(
            data_spec=data_spec,
            parameter_grid={
                "short_window": args.short_windows,
                "long_window": args.long_windows,
            },
            backtest_config=backtest_config,
            output_dir=args.output_dir,
            experiment_name=args.experiment_name,
            max_drawdown_cap=args.max_drawdown_cap,
            min_trade_count=args.min_trade_count,
            generate_best_report=args.generate_report,
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
