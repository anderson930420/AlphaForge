"""Deterministic Mom12m OAP / JKP first-factor pipeline.

Phase 15 stitches together the local contract, loader, signal adapter, custom
signal consumer, and signed AlphaForge backtest runtime for a local CSV smoke.
It does not download remote OAP / JKP data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from alphaforge.backtest import SIGNED_EXECUTION_SEMANTICS, run_backtest
from alphaforge.custom_signal import load_custom_signal_positions
from alphaforge.oap_factor_contract import OAPFactorContract, load_oap_factor_contract
from alphaforge.oap_loader import load_oap_factor_frame
from alphaforge.oap_signal_adapter import build_oap_signal_frame_from_factor_frame
from alphaforge.schemas import BacktestConfig


@dataclass(frozen=True)
class OAPMom12mPipelineResult:
    contract: OAPFactorContract
    factor_frame: pd.DataFrame
    signal_frame: pd.DataFrame
    target_positions: pd.Series
    signal_metadata: dict[str, object]
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    signal_output_path: Path


def run_oap_mom12m_pipeline_smoke(
    *,
    characteristics_path: str | Path,
    contract_path: str | Path,
    market_data: pd.DataFrame,
    signal_output_path: str | Path,
    symbol: str | None = None,
    backtest_config: BacktestConfig | None = None,
) -> OAPMom12mPipelineResult:
    """Run the local Mom12m factor pipeline through AlphaForge backtest smoke.

    Inputs are intentionally local and deterministic. The function writes the
    generated v0.2 signal frame to `signal_output_path`, consumes that file via
    the existing custom_signal path, and runs the signed long/short runtime.
    """
    contract = load_oap_factor_contract(contract_path)
    if contract.factor.get("name") != "Mom12m":
        raise ValueError("Phase 15 pipeline smoke expects a Mom12m factor contract")

    factor_frame = load_oap_factor_frame(characteristics_path, contract)
    signal_frame = build_oap_signal_frame_from_factor_frame(factor_frame, contract)

    output_path = Path(signal_output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    signal_frame.to_csv(output_path, index=False)

    config = backtest_config or BacktestConfig(
        initial_capital=1000.0,
        fee_rate=0.0,
        slippage_rate=0.0,
        annualization_factor=252,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )
    target_positions, signal_metadata = load_custom_signal_positions(output_path, market_data, symbol=symbol)
    equity_curve, trades = run_backtest(
        market_data,
        target_positions,
        config,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )

    return OAPMom12mPipelineResult(
        contract=contract,
        factor_frame=factor_frame,
        signal_frame=signal_frame,
        target_positions=target_positions,
        signal_metadata=signal_metadata,
        equity_curve=equity_curve,
        trades=trades,
        signal_output_path=output_path,
    )
