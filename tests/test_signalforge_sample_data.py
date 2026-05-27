from __future__ import annotations

from pathlib import Path

from alphaforge.signalforge_package import run_signalforge_v02_package_smoke


SAMPLE_PACKAGE = Path("sample_data/signalforge/demo_v02_package")


def test_signalforge_sample_data_package_smoke() -> None:
    result = run_signalforge_v02_package_smoke(SAMPLE_PACKAGE)

    assert result.market_data_row_count == 4
    assert result.signal_row_count == 4
    assert result.signal_metadata["signal_contract_version"] == "v0.2"
    assert result.signal_metadata["target_position_source_column"] == "target_weight"
    assert result.manifest["alpha_forge_strategy"] == "custom_signal"
    assert result.manifest["expected_alpha_forge_execution_semantics"] == "signed_close_to_close_lagged"
    assert result.equity_curve["target_position"].tolist() == [0.0, 1.0, -1.0, 0.0]
    assert result.equity_curve["position"].tolist() == [0.0, 0.0, 1.0, -1.0]
    assert result.trades.shape[0] == 2


def test_signalforge_sample_data_package_files_are_documented() -> None:
    expected_files = {
        "market_data.csv",
        "signal.csv",
        "signal_contract.yaml",
        "data_quality_report.json",
        "manifest.json",
        "README.md",
    }

    assert SAMPLE_PACKAGE.exists()
    assert {path.name for path in SAMPLE_PACKAGE.iterdir() if path.is_file()} == expected_files

    readme = (SAMPLE_PACKAGE / "README.md").read_text(encoding="utf-8")
    assert "smoke-signalforge-package" in readme
    assert "target_weight" in readme
    assert "signed_close_to_close_lagged" in readme
