from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.oap_real_data_cli import main
from alphaforge.open_asset_pricing import OAP_SIGNAL_COLUMNS


CONTRACT_FIXTURE = Path("tests/fixtures/oap_factor_contracts/mom12m_threshold.yaml")


def _write_characteristics(path: Path) -> None:
    pd.DataFrame(
        {
            "date": ["2024-01-31", "2024-02-29", "2024-03-31"],
            "permno": ["10001", "10001", "10001"],
            "symbol": ["AAA", "AAA", "AAA"],
            "Mom12m": [0.2, -0.1, 0.0],
        }
    ).to_csv(path, index=False)


def _write_market_data(path: Path) -> None:
    pd.DataFrame(
        {
            "datetime": ["2024-02-01", "2024-03-01", "2024-04-01"],
            "open": [10.0, 11.0, 9.0],
            "high": [10.0, 11.0, 9.0],
            "low": [10.0, 11.0, 9.0],
            "close": [10.0, 11.0, 9.0],
            "volume": [100, 100, 100],
            "symbol": ["AAA", "AAA", "AAA"],
        }
    ).to_csv(path, index=False)


def test_oap_real_data_cli_writes_signal_report_and_prints_summary(tmp_path, monkeypatch, capsys) -> None:
    characteristics_path = tmp_path / "mom12m_real.csv"
    market_data_path = tmp_path / "market.csv"
    signal_output_path = tmp_path / "signal.csv"
    report_output_path = tmp_path / "report.json"
    _write_characteristics(characteristics_path)
    _write_market_data(market_data_path)

    monkeypatch.setattr(
        "sys.argv",
        [
            "alphaforge-oap-real-data",
            "--characteristics",
            str(characteristics_path),
            "--contract",
            str(CONTRACT_FIXTURE),
            "--market-data",
            str(market_data_path),
            "--signal-output",
            str(signal_output_path),
            "--report-output",
            str(report_output_path),
            "--symbol",
            "AAA",
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
    assert summary["workflow"] == "oap_mom12m_real_data_local"
    assert summary["inputs"]["characteristics"] == str(characteristics_path)
    assert summary["inputs"]["contract"] == str(CONTRACT_FIXTURE)
    assert summary["inputs"]["market_data"] == str(market_data_path)
    assert summary["inputs"]["symbol"] == "AAA"
    assert summary["outputs"]["signal_output"] == str(signal_output_path)
    assert summary["outputs"]["report_output"] == str(report_output_path)
    assert summary["contract"]["factor_name"] == "Mom12m"
    assert summary["factor_frame"]["row_count"] == 3
    assert summary["signal_frame"]["direction_counts"] == {"-1": 1, "0": 1, "1": 1}
    assert summary["signal_frame"]["target_weight_counts"] == {"-1.0": 1, "0.0": 1, "1.0": 1}
    assert summary["backtest"]["initial_capital"] == pytest.approx(1000.0)
    assert summary["backtest"]["fee_rate"] == pytest.approx(0.0)
    assert summary["backtest"]["slippage_rate"] == pytest.approx(0.0)
    assert summary["backtest"]["final_equity"] == pytest.approx(1300.0)

    signal_output = pd.read_csv(signal_output_path)
    assert signal_output.columns.tolist() == list(OAP_SIGNAL_COLUMNS)
    assert signal_output["target_weight"].tolist() == [1.0, -1.0, 0.0]

    persisted_report = json.loads(report_output_path.read_text(encoding="utf-8"))
    assert persisted_report["status"] == "passed"
    assert persisted_report["outputs"]["signal_output"] == str(signal_output_path)
    assert "report_output" not in persisted_report["outputs"]


def test_oap_real_data_cli_respects_custom_cost_arguments(tmp_path, monkeypatch, capsys) -> None:
    characteristics_path = tmp_path / "mom12m_real.csv"
    market_data_path = tmp_path / "market.csv"
    signal_output_path = tmp_path / "signal.csv"
    report_output_path = tmp_path / "report.json"
    _write_characteristics(characteristics_path)
    _write_market_data(market_data_path)

    monkeypatch.setattr(
        "sys.argv",
        [
            "alphaforge-oap-real-data",
            "--characteristics",
            str(characteristics_path),
            "--contract",
            str(CONTRACT_FIXTURE),
            "--market-data",
            str(market_data_path),
            "--signal-output",
            str(signal_output_path),
            "--report-output",
            str(report_output_path),
            "--symbol",
            "AAA",
            "--initial-capital",
            "500",
            "--fee-rate",
            "0",
            "--slippage-rate",
            "0",
        ],
    )

    main()

    summary = json.loads(capsys.readouterr().out)
    assert summary["backtest"]["initial_capital"] == pytest.approx(500.0)
    assert summary["backtest"]["final_equity"] == pytest.approx(650.0)
