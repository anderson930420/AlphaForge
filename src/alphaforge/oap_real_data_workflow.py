"""Local real-data workflow helpers for OAP / JKP Mom12m runs.

Phase 17 does not download or commit external data. It provides a deterministic
reporting layer around the existing local Mom12m pipeline so users can run their
own OAP / JKP-style CSV files and inspect data alignment, signal distribution,
and backtest smoke outputs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from alphaforge.backtest import SIGNED_EXECUTION_SEMANTICS
from alphaforge.oap_mom12m_pipeline import OAPMom12mPipelineResult, run_oap_mom12m_pipeline_smoke
from alphaforge.schemas import BacktestConfig


@dataclass(frozen=True)
class OAPMom12mRealDataWorkflowResult:
    """Result bundle for a local real-data Mom12m workflow run."""

    pipeline_result: OAPMom12mPipelineResult
    summary: dict[str, Any]
    report_output_path: Path | None = None


def run_oap_mom12m_real_data_local_workflow(
    *,
    characteristics_path: str | Path,
    contract_path: str | Path,
    market_data_path: str | Path,
    signal_output_path: str | Path,
    report_output_path: str | Path | None = None,
    symbol: str | None = None,
    backtest_config: BacktestConfig | None = None,
) -> OAPMom12mRealDataWorkflowResult:
    """Run a local Mom12m workflow and build a data-quality/report summary.

    This function is intended for local real-data CSV files. It reads local market
    data, runs the Phase 15 Mom12m pipeline, writes the generated signal CSV, and
    optionally writes a JSON summary report. No remote data access is performed.
    """
    resolved_config = backtest_config or BacktestConfig(
        initial_capital=1000.0,
        fee_rate=0.0,
        slippage_rate=0.0,
        annualization_factor=252,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )
    market_data = pd.read_csv(Path(market_data_path))
    pipeline_result = run_oap_mom12m_pipeline_smoke(
        characteristics_path=characteristics_path,
        contract_path=contract_path,
        market_data=market_data,
        signal_output_path=signal_output_path,
        symbol=symbol,
        backtest_config=resolved_config,
    )
    summary = build_oap_mom12m_real_data_summary(
        pipeline_result,
        characteristics_path=characteristics_path,
        contract_path=contract_path,
        market_data_path=market_data_path,
        symbol=symbol,
        backtest_config=resolved_config,
    )

    output_path = Path(report_output_path) if report_output_path is not None else None
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    return OAPMom12mRealDataWorkflowResult(
        pipeline_result=pipeline_result,
        summary=summary,
        report_output_path=output_path,
    )


def build_oap_mom12m_real_data_summary(
    pipeline_result: OAPMom12mPipelineResult,
    *,
    characteristics_path: str | Path,
    contract_path: str | Path,
    market_data_path: str | Path,
    symbol: str | None,
    backtest_config: BacktestConfig,
) -> dict[str, Any]:
    """Build a JSON-serializable summary for local real-data inspection."""
    factor_frame = pipeline_result.factor_frame
    signal_frame = pipeline_result.signal_frame
    equity_curve = pipeline_result.equity_curve
    trades = pipeline_result.trades

    return {
        "status": "passed",
        "workflow": "oap_mom12m_real_data_local",
        "inputs": {
            "characteristics": str(characteristics_path),
            "contract": str(contract_path),
            "market_data": str(market_data_path),
            "symbol": symbol,
        },
        "outputs": {
            "signal_output": str(pipeline_result.signal_output_path),
        },
        "contract": {
            "version": pipeline_result.contract.version,
            "factor_name": str(pipeline_result.contract.factor["name"]),
            "decision_rule_type": str(pipeline_result.contract.decision_rule["type"]),
            "target_weight_mode": str(pipeline_result.contract.weighting["target_weight_mode"]),
            "available_at_policy": str(pipeline_result.contract.timing["available_at_policy"]),
        },
        "factor_frame": {
            "row_count": int(len(factor_frame)),
            "symbol_count": int(factor_frame["symbol"].nunique()),
            "date_min": _maybe_iso_date(factor_frame["datetime"].min()),
            "date_max": _maybe_iso_date(factor_frame["datetime"].max()),
            "available_at_min": _maybe_iso_date(factor_frame["available_at"].min()),
            "available_at_max": _maybe_iso_date(factor_frame["available_at"].max()),
            "missing_factor_value_count": int(factor_frame["factor_value"].isna().sum()),
            "factor_value_min": _maybe_float(factor_frame["factor_value"].min()),
            "factor_value_max": _maybe_float(factor_frame["factor_value"].max()),
            "factor_value_mean": _maybe_float(factor_frame["factor_value"].mean()),
        },
        "signal_frame": {
            "row_count": int(len(signal_frame)),
            "symbol_count": int(signal_frame["symbol"].nunique()),
            "date_min": _maybe_iso_date(signal_frame["datetime"].min()),
            "date_max": _maybe_iso_date(signal_frame["datetime"].max()),
            "available_at_min": _maybe_iso_date(signal_frame["available_at"].min()),
            "available_at_max": _maybe_iso_date(signal_frame["available_at"].max()),
            "direction_counts": _value_counts(signal_frame["direction"]),
            "target_weight_counts": _value_counts(signal_frame["target_weight"]),
        },
        "backtest": {
            "execution_semantics": SIGNED_EXECUTION_SEMANTICS,
            "initial_capital": float(backtest_config.initial_capital),
            "fee_rate": float(backtest_config.fee_rate),
            "slippage_rate": float(backtest_config.slippage_rate),
            "equity_curve_rows": int(len(equity_curve)),
            "trade_count": int(len(trades)),
            "final_equity": _maybe_float(equity_curve["equity"].iloc[-1]) if len(equity_curve) else None,
            "min_equity": _maybe_float(equity_curve["equity"].min()) if len(equity_curve) else None,
            "max_equity": _maybe_float(equity_curve["equity"].max()) if len(equity_curve) else None,
            "turnover_sum": _maybe_float(equity_curve["turnover"].sum()) if len(equity_curve) else None,
        },
        "signal_metadata": dict(pipeline_result.signal_metadata),
    }


def _value_counts(series: pd.Series) -> dict[str, int]:
    counts = series.value_counts(dropna=False).sort_index()
    return {str(key): int(value) for key, value in counts.items()}


def _maybe_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _maybe_iso_date(value: Any) -> str | None:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")
