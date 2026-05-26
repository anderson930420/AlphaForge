from __future__ import annotations

import json

import pandas as pd

from alphaforge.backtest import SIGNED_EXECUTION_SEMANTICS
from alphaforge.signalforge_package import (
    SIGNALFORGE_V02_REQUIRED_FILES,
    run_signalforge_v02_package_smoke,
)


def _write_signalforge_v02_package(package_dir):
    package_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        {
            "datetime": ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"],
            "open": [100.0, 101.0, 99.0, 100.0],
            "high": [102.0, 102.0, 101.0, 101.0],
            "low": [99.0, 98.0, 98.0, 99.0],
            "close": [101.0, 99.0, 100.0, 100.5],
            "volume": [1000, 1100, 1200, 1300],
        }
    ).to_csv(package_dir / "market_data.csv", index=False)

    pd.DataFrame(
        {
            "datetime": ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"],
            "available_at": ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"],
            "symbol": ["SFDEMO", "SFDEMO", "SFDEMO", "SFDEMO"],
            "signal_name": ["sf_v02_demo", "sf_v02_demo", "sf_v02_demo", "sf_v02_demo"],
            "score": [0.0, 1.25, -1.0, 0.0],
            "direction": [0, 1, -1, 0],
            "target_weight": [0.0, 1.0, -1.0, 0.0],
            "source": ["SignalForge", "SignalForge", "SignalForge", "SignalForge"],
        }
    ).to_csv(package_dir / "signal.csv", index=False)

    (package_dir / "signal_contract.yaml").write_text(
        """signal_name: sf_v02_demo
version: 0.2.0
source: SignalForge
output:
  file: signal.csv
  schema_version: v0.2
compatibility:
  alphaforge_strategy: custom_signal
  alphaforge_custom_signal_version: v0.2
  expected_execution_semantics: signed_close_to_close_lagged
""",
        encoding="utf-8",
    )

    (package_dir / "manifest.json").write_text(
        json.dumps(
            {
                "package_name": "alphaforge_v02_compatibility_smoke_export",
                "package_version": "1.0.0",
                "generator": "SignalForge",
                "schema_version": "v0.2",
                "alpha_forge_strategy": "custom_signal",
                "expected_alpha_forge_execution_semantics": "signed_close_to_close_lagged",
                "contains_backtest_results": False,
                "contains_performance_metrics": False,
                "market_data_file": "market_data.csv",
                "signal_file": "signal.csv",
                "signal_contract_file": "signal_contract.yaml",
                "data_quality_report_file": "data_quality_report.json",
                "row_count": 4,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    (package_dir / "data_quality_report.json").write_text(
        '{"generator":"SignalForge"}\n',
        encoding="utf-8",
    )
    (package_dir / "README.md").write_text(
        "AlphaForge consumes files only in this smoke package.\n",
        encoding="utf-8",
    )


def test_run_signalforge_v02_package_smoke_consumes_package_and_runs_signed_runtime(tmp_path) -> None:
    _write_signalforge_v02_package(tmp_path)

    result = run_signalforge_v02_package_smoke(tmp_path)

    assert result.market_data_row_count == 4
    assert result.signal_row_count == 4
    assert result.manifest["generator"] == "SignalForge"
    assert result.signal_metadata["signal_contract_version"] == "v0.2"
    assert result.signal_metadata["target_position_source_column"] == "target_weight"
    assert result.equity_curve["target_position"].tolist() == [0.0, 1.0, -1.0, 0.0]
    assert result.equity_curve["position"].tolist() == [0.0, 0.0, 1.0, -1.0]
    assert result.trades.shape[0] == 2


def test_signalforge_v02_package_smoke_requires_all_package_files(tmp_path) -> None:
    _write_signalforge_v02_package(tmp_path)
    (tmp_path / "manifest.json").unlink()

    try:
        run_signalforge_v02_package_smoke(tmp_path)
    except ValueError as exc:
        assert "Missing required SignalForge package files" in str(exc)
        assert "manifest.json" in str(exc)
    else:
        raise AssertionError("expected missing manifest failure")


def test_signalforge_v02_package_smoke_rejects_wrong_execution_semantics_manifest(tmp_path) -> None:
    _write_signalforge_v02_package(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["expected_alpha_forge_execution_semantics"] = "legacy_close_to_close_lagged"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    try:
        run_signalforge_v02_package_smoke(tmp_path)
    except ValueError as exc:
        assert "expected_alpha_forge_execution_semantics" in str(exc)
        assert SIGNED_EXECUTION_SEMANTICS in str(exc)
    else:
        raise AssertionError("expected execution semantics manifest failure")


def test_signalforge_v02_package_smoke_rejects_performance_claims(tmp_path) -> None:
    _write_signalforge_v02_package(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["contains_performance_metrics"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    try:
        run_signalforge_v02_package_smoke(tmp_path)
    except ValueError as exc:
        assert "performance metrics" in str(exc)
    else:
        raise AssertionError("expected performance metrics claim failure")


def test_signalforge_required_file_list_matches_expected_package_boundary() -> None:
    assert SIGNALFORGE_V02_REQUIRED_FILES == (
        "market_data.csv",
        "signal.csv",
        "signal_contract.yaml",
        "data_quality_report.json",
        "manifest.json",
        "README.md",
    )
