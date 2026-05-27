"""CLI entrypoint for local OAP / JKP Mom12m real-data reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphaforge import config
from alphaforge.backtest import SIGNED_EXECUTION_SEMANTICS
from alphaforge.oap_real_data_workflow import run_oap_mom12m_real_data_local_workflow
from alphaforge.schemas import BacktestConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local OAP / JKP Mom12m real-data workflow and write a JSON report")
    parser.add_argument("--characteristics", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--market-data", required=True, type=Path)
    parser.add_argument("--signal-output", required=True, type=Path)
    parser.add_argument("--report-output", required=True, type=Path)
    parser.add_argument("--symbol", type=str, default=None)
    parser.add_argument("--initial-capital", type=float, default=config.INITIAL_CAPITAL)
    parser.add_argument("--fee-rate", type=float, default=config.DEFAULT_FEE_RATE)
    parser.add_argument("--slippage-rate", type=float, default=config.DEFAULT_SLIPPAGE_RATE)
    parser.add_argument("--annualization-factor", type=int, default=config.DEFAULT_ANNUALIZATION)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    backtest_config = BacktestConfig(
        initial_capital=args.initial_capital,
        fee_rate=args.fee_rate,
        slippage_rate=args.slippage_rate,
        annualization_factor=args.annualization_factor,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )
    result = run_oap_mom12m_real_data_local_workflow(
        characteristics_path=args.characteristics,
        contract_path=args.contract,
        market_data_path=args.market_data,
        signal_output_path=args.signal_output,
        report_output_path=args.report_output,
        symbol=args.symbol,
        backtest_config=backtest_config,
    )
    summary = dict(result.summary)
    summary["outputs"] = dict(summary["outputs"])
    summary["outputs"]["report_output"] = str(result.report_output_path)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
