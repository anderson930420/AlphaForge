#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from alphaforge.crsp_momentum import (
    build_momentum_portfolio_returns,
    compute_mom12_1,
    summarize_momentum_returns,
)
from alphaforge.crsp_monthly_panel import load_crsp_monthly_panel
from alphaforge.json_utils import write_json_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a deterministic CRSP Mom12m skip-1 long-short baseline"
    )
    parser.add_argument("--input", required=True, type=Path, help="External CRSP monthly parquet panel")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for baseline artifacts")
    parser.add_argument("--start-date", default=None, type=str, help="Optional signal window start date")
    parser.add_argument("--end-date", default=None, type=str, help="Optional signal window end date")
    parser.add_argument("--quantile", type=float, default=0.1)
    parser.add_argument("--min-obs", type=int, default=8)
    parser.add_argument("--weighting", choices=("equal", "value"), default="equal")
    parser.add_argument("--common-shares-only", action="store_true")
    parser.add_argument("--primary-exchange-only", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    start_date = _parse_optional_date(args.start_date, field_name="start_date")
    end_date = _parse_optional_date(args.end_date, field_name="end_date")
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date must be on or before end_date")

    panel = load_crsp_monthly_panel(
        args.input,
        common_shares_only=args.common_shares_only,
        primary_exchange_only=args.primary_exchange_only,
    )

    signal_panel = compute_mom12_1(
        panel,
        return_col="total_ret",
        min_obs=args.min_obs,
    )
    signal_panel["forward_1m_total_ret"] = signal_panel.groupby("asset_id", sort=False)["total_ret"].shift(-1)
    signal_panel = _filter_signal_window(signal_panel, start_date=start_date, end_date=end_date)

    signal_panel_path = output_dir / "momentum_signal_panel.parquet"
    signal_panel.to_parquet(signal_panel_path, index=False)

    portfolio_returns = build_momentum_portfolio_returns(
        signal_panel,
        signal_col="mom12_1",
        return_col="forward_1m_total_ret",
        quantile=args.quantile,
        weighting=args.weighting,
    )
    portfolio_returns_path = output_dir / "momentum_portfolio_returns.parquet"
    portfolio_returns.to_parquet(portfolio_returns_path, index=False)

    portfolio_summary = summarize_momentum_returns(portfolio_returns)
    summary_payload = {
        "status": "ok",
        "input": str(args.input),
        "output_dir": str(output_dir),
        "start_date": args.start_date,
        "end_date": args.end_date,
        "quantile": float(args.quantile),
        "min_obs": int(args.min_obs),
        "weighting": args.weighting,
        "common_shares_only": bool(args.common_shares_only),
        "primary_exchange_only": bool(args.primary_exchange_only),
        "signal_panel_path": str(signal_panel_path),
        "portfolio_returns_path": str(portfolio_returns_path),
        "signal_panel_rows": int(len(signal_panel)),
        "portfolio_rows": int(len(portfolio_returns)),
        **portfolio_summary,
    }

    summary_path = output_dir / "momentum_summary.json"
    summary_payload["summary_path"] = str(summary_path)
    write_json_artifact(summary_path, summary_payload)

    print(json.dumps(summary_payload, indent=2, sort_keys=True, default=str))


def _filter_signal_window(
    signal_panel: pd.DataFrame,
    *,
    start_date: pd.Timestamp | None,
    end_date: pd.Timestamp | None,
) -> pd.DataFrame:
    frame = signal_panel.copy()
    if start_date is not None:
        frame = frame.loc[frame["date"] >= start_date]
    if end_date is not None:
        frame = frame.loc[frame["date"] <= end_date]
    return frame.reset_index(drop=True)


def _parse_optional_date(value: str | None, *, field_name: str) -> pd.Timestamp | None:
    if value is None:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"{field_name} must be parseable as datetime: {value!r}")
    return pd.Timestamp(parsed)


if __name__ == "__main__":
    main()
