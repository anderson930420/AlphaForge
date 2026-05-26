"""SignalForge v0.2 package compatibility smoke utilities.

AlphaForge consumes SignalForge artifacts through files only. This module does
not import SignalForge internals and does not create a new signal schema. It
validates a SignalForge-produced package, loads `signal.csv` through the
existing custom_signal v0.2 loader, and runs the signed backtest runtime.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .backtest import SIGNED_EXECUTION_SEMANTICS, run_backtest
from .custom_signal import SIGNAL_CONTRACT_V2, load_custom_signal_positions
from .schemas import BacktestConfig, EquityCurveFrame

SIGNALFORGE_V02_REQUIRED_FILES = (
    "market_data.csv",
    "signal.csv",
    "signal_contract.yaml",
    "data_quality_report.json",
    "manifest.json",
    "README.md",
)
SIGNALFORGE_PACKAGE_GENERATOR = "SignalForge"
ALPHAFORGE_CUSTOM_SIGNAL_STRATEGY = "custom_signal"
ALPHAFORGE_CUSTOM_SIGNAL_VERSION = SIGNAL_CONTRACT_V2


@dataclass(frozen=True)
class SignalForgePackageSmokeResult:
    """Result of consuming a SignalForge v0.2 compatibility package."""

    package_dir: Path
    market_data_row_count: int
    signal_row_count: int
    manifest: dict[str, Any]
    signal_metadata: dict[str, object]
    equity_curve: EquityCurveFrame
    trades: pd.DataFrame


def run_signalforge_v02_package_smoke(
    package_dir: Path | str,
    *,
    backtest_config: BacktestConfig | None = None,
) -> SignalForgePackageSmokeResult:
    """Validate and backtest a SignalForge v0.2 compatibility package.

    The package must contain the files emitted by SignalForge SF-4. AlphaForge
    treats `manifest.json` as the machine-readable compatibility contract and
    uses the existing `custom_signal` loader to consume `signal.csv`.
    """
    package_path = Path(package_dir)
    _validate_required_files(package_path)

    manifest = _read_manifest(package_path / "manifest.json")
    _validate_manifest(manifest)
    _validate_contract_text(package_path / "signal_contract.yaml")

    market_data = pd.read_csv(package_path / "market_data.csv")
    target_positions, signal_metadata = load_custom_signal_positions(
        package_path / "signal.csv",
        market_data,
    )
    _validate_signal_metadata(signal_metadata)

    config = backtest_config or BacktestConfig(
        initial_capital=1000.0,
        fee_rate=0.0,
        slippage_rate=0.0,
        annualization_factor=252,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )
    if config.execution_semantics != SIGNED_EXECUTION_SEMANTICS:
        raise ValueError(
            "SignalForge v0.2 packages require signed_close_to_close_lagged execution semantics"
        )

    equity_curve, trades = run_backtest(
        market_data,
        target_positions,
        config,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )

    return SignalForgePackageSmokeResult(
        package_dir=package_path,
        market_data_row_count=int(len(market_data)),
        signal_row_count=int(signal_metadata["signal_row_count"]),
        manifest=manifest,
        signal_metadata=signal_metadata,
        equity_curve=equity_curve,
        trades=trades,
    )


def _validate_required_files(package_dir: Path) -> None:
    if not package_dir.exists() or not package_dir.is_dir():
        raise ValueError(f"SignalForge package directory does not exist: {package_dir}")
    missing = [name for name in SIGNALFORGE_V02_REQUIRED_FILES if not (package_dir / name).exists()]
    if missing:
        raise ValueError(f"Missing required SignalForge package files: {missing}")


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse SignalForge manifest.json: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("SignalForge manifest.json must contain a JSON object")
    return data


def _validate_manifest(manifest: dict[str, Any]) -> None:
    expected_values = {
        "generator": SIGNALFORGE_PACKAGE_GENERATOR,
        "schema_version": SIGNAL_CONTRACT_V2,
        "alpha_forge_strategy": ALPHAFORGE_CUSTOM_SIGNAL_STRATEGY,
        "expected_alpha_forge_execution_semantics": SIGNED_EXECUTION_SEMANTICS,
    }
    for key, expected in expected_values.items():
        actual = manifest.get(key)
        if actual != expected:
            raise ValueError(f"SignalForge manifest {key!r} must be {expected!r}, got {actual!r}")

    if manifest.get("contains_backtest_results") is not False:
        raise ValueError("SignalForge package must not claim to contain backtest results")
    if manifest.get("contains_performance_metrics") is not False:
        raise ValueError("SignalForge package must not claim to contain performance metrics")


def _validate_contract_text(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    required_fragments = (
        "schema_version: v0.2",
        "alphaforge_custom_signal_version: v0.2",
        "expected_execution_semantics: signed_close_to_close_lagged",
        "alphaforge_strategy: custom_signal",
    )
    missing = [fragment for fragment in required_fragments if fragment not in text]
    if missing:
        raise ValueError(f"SignalForge signal_contract.yaml missing required fragments: {missing}")


def _validate_signal_metadata(signal_metadata: dict[str, object]) -> None:
    expected = {
        "signal_contract_version": SIGNAL_CONTRACT_V2,
        "target_position_source_column": "target_weight",
    }
    for key, expected_value in expected.items():
        actual = signal_metadata.get(key)
        if actual != expected_value:
            raise ValueError(f"custom_signal metadata {key!r} must be {expected_value!r}, got {actual!r}")
