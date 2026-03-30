from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from . import config
from .experiment_runner import run_experiment, run_search
from .report import render_experiment_report, save_experiment_report
from .schemas import BacktestConfig, DataSpec, StrategySpec
from .storage import ensure_output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AlphaForge MVP CLI")
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
            ranked = run_search(
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
            report_path = _build_search_report_path(args.output_dir, args.experiment_name) if args.generate_report and ranked else None
            search_report_path = _build_search_comparison_report_path(args.output_dir, args.experiment_name) if args.generate_report else None
            print(
                json.dumps(
                    _build_search_summary(
                        ranked,
                        args.output_dir,
                        args.experiment_name,
                        data_output=data_output,
                        report_path=report_path,
                        search_report_path=search_report_path,
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
            result, equity_curve, trades = run_experiment(
                data_spec=data_spec,
                strategy_spec=strategy_spec,
                backtest_config=backtest_config,
                output_dir=args.output_dir,
                experiment_name=args.experiment_name,
            )
            payload = result.to_dict()
            if args.generate_report:
                experiment_dir = ensure_output_dir(args.output_dir / args.experiment_name)
                report_content = render_experiment_report(result, equity_curve, trades)
                report_path = save_experiment_report(report_content, experiment_dir / "report.html")
                payload["report_path"] = str(report_path)
            print(json.dumps(payload, indent=2, default=str))
            return

        ranked = run_search(
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
        report_path = _build_search_report_path(args.output_dir, args.experiment_name) if args.generate_report and ranked else None
        search_report_path = _build_search_comparison_report_path(args.output_dir, args.experiment_name) if args.generate_report else None
        print(
            json.dumps(
                _build_search_summary(
                    ranked,
                    args.output_dir,
                    args.experiment_name,
                    report_path=report_path,
                    search_report_path=search_report_path,
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
    ranked,
    output_dir: Path,
    experiment_name: str,
    data_output: Path | None = None,
    report_path: Path | None = None,
    search_report_path: Path | None = None,
) -> dict:
    search_root = output_dir / experiment_name
    payload = {
        "result_count": len(ranked),
        "ranked_results_path": str(search_root / "ranked_results.csv"),
        "top_results": [result.to_dict() for result in ranked[:3]],
    }
    if ranked:
        payload["best_result"] = ranked[0].to_dict()
    else:
        payload["best_result"] = None
    if data_output is not None:
        payload["data_output"] = str(data_output)
    if report_path is not None:
        payload["report_path"] = str(report_path)
    if search_report_path is not None:
        payload["search_report_path"] = str(search_report_path)
    return payload


def _build_search_report_path(output_dir: Path, experiment_name: str) -> Path:
    return output_dir / experiment_name / "best_report.html"


def _build_search_comparison_report_path(output_dir: Path, experiment_name: str) -> Path:
    return output_dir / experiment_name / "search_report.html"


if __name__ == "__main__":
    main()
