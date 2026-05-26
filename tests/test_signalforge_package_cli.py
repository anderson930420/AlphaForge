from __future__ import annotations

import json

import pandas as pd

from alphaforge.cli import main


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


def test_smoke_signalforge_package_cli_prints_pass_summary(tmp_path, monkeypatch, capsys) -> None:
    _write_signalforge_v02_package(tmp_path)

    monkeypatch.setattr(
        "sys.argv",
        [
            "alphaforge",
            "smoke-signalforge-package",
            "--package",
            str(tmp_path),
            "--initial-capital",
            "1000",
            "--fee-rate",
            "0",
            "--slippage-rate",
            "0",
        ],
    )

    main()

    summary = json.loads(capsys.readouterr().out)

    assert summary["status"] == "passed"
    assert summary["package"] == str(tmp_path)
    assert summary["market_data_row_count"] == 4
    assert summary["signal_row_count"] == 4
    assert summary["signal_contract_version"] == "v0.2"
    assert summary["target_position_source_column"] == "target_weight"
    assert summary["execution_semantics"] == "signed_close_to_close_lagged"
    assert summary["equity_curve_rows"] == 4
    assert summary["trade_count"] == 2
    assert isinstance(summary["final_equity"], float)


def test_smoke_signalforge_package_cli_is_registered() -> None:
    from alphaforge.cli import build_parser

    parser = build_parser()
    commands = parser._subparsers._group_actions[0].choices

    assert "smoke-signalforge-package" in commands
