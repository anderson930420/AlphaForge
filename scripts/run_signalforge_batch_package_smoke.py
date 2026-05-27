#!/usr/bin/env python3
"""Run AlphaForge smoke checks across multiple SignalForge v0.2 packages.

This script is a batch wrapper around the existing single-package compatibility
smoke. It consumes SignalForge package directories as files only and does not
import SignalForge internals.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from alphaforge.backtest import SIGNED_EXECUTION_SEMANTICS
from alphaforge.schemas import BacktestConfig
from alphaforge.signalforge_package import (
    SIGNALFORGE_V02_REQUIRED_FILES,
    run_signalforge_v02_package_smoke,
)


def is_signalforge_v02_package_dir(path: Path) -> bool:
    """Return true when path looks like a complete SignalForge v0.2 package."""
    return path.is_dir() and all((path / filename).exists() for filename in SIGNALFORGE_V02_REQUIRED_FILES)


def discover_signalforge_v02_package_dirs(packages_root: Path | str) -> list[Path]:
    """Discover package directories under a root.

    If the root itself is a package, return it. Otherwise, return immediate child
    directories that contain the required SignalForge package files.
    """
    root = Path(packages_root)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"SignalForge packages root does not exist or is not a directory: {root}")

    if is_signalforge_v02_package_dir(root):
        return [root]

    package_dirs = sorted(
        child for child in root.iterdir() if child.is_dir() and is_signalforge_v02_package_dir(child)
    )
    if not package_dirs:
        raise ValueError(f"No SignalForge v0.2 package directories found under: {root}")
    return package_dirs


def run_signalforge_batch_package_smoke(
    packages_root: Path | str,
    *,
    backtest_config: BacktestConfig | None = None,
) -> dict[str, Any]:
    """Run package smoke checks for every SignalForge package under packages_root."""
    root = Path(packages_root)
    config = backtest_config or BacktestConfig(
        initial_capital=1000.0,
        fee_rate=0.0,
        slippage_rate=0.0,
        annualization_factor=252,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )

    entries: list[dict[str, Any]] = []
    for package_dir in discover_signalforge_v02_package_dirs(root):
        try:
            result = run_signalforge_v02_package_smoke(package_dir, backtest_config=config)
            entries.append(
                {
                    "status": "passed",
                    "package": str(package_dir),
                    "market_data_row_count": result.market_data_row_count,
                    "signal_row_count": result.signal_row_count,
                    "signal_contract_version": result.signal_metadata.get("signal_contract_version"),
                    "target_position_source_column": result.signal_metadata.get("target_position_source_column"),
                    "execution_semantics": SIGNED_EXECUTION_SEMANTICS,
                    "equity_curve_rows": int(len(result.equity_curve)),
                    "trade_count": int(len(result.trades)),
                    "final_equity": float(result.equity_curve["equity"].iloc[-1]),
                }
            )
        except Exception as exc:  # pragma: no cover - exact exception class depends on package failure mode.
            entries.append(
                {
                    "status": "failed",
                    "package": str(package_dir),
                    "error": str(exc),
                }
            )

    passed_count = sum(1 for entry in entries if entry["status"] == "passed")
    failed_count = len(entries) - passed_count
    return {
        "status": "passed" if failed_count == 0 else "failed",
        "packages_root": str(root),
        "package_count": len(entries),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "packages": entries,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run batch smoke checks for SignalForge v0.2 packages")
    parser.add_argument("--packages-root", type=Path, required=True, help="Directory containing SignalForge packages")
    parser.add_argument("--summary-output", type=Path, default=None, help="Optional JSON summary output path")
    parser.add_argument("--initial-capital", type=float, default=1000.0)
    parser.add_argument("--fee-rate", type=float, default=0.0)
    parser.add_argument("--slippage-rate", type=float, default=0.0)
    parser.add_argument("--annualization-factor", type=int, default=252)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = BacktestConfig(
        initial_capital=args.initial_capital,
        fee_rate=args.fee_rate,
        slippage_rate=args.slippage_rate,
        annualization_factor=args.annualization_factor,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )
    summary = run_signalforge_batch_package_smoke(args.packages_root, backtest_config=config)

    if args.summary_output is not None:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
