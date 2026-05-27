from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.cli import main
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


def test_run_oap_mom12m_pipeline_cli_writes_signal_and_prints_summary(tmp_path, monkeypatch, capsys) -> None:
    characteristics_path = tmp_path / "mom12m.csv"
    market_data_path = tmp_path / "market.csv"
    signal_output_path = tmp_path / "signal.csv"
    _write_characteristics(characteristics_path)
    _write_market_data(market_data_path)

    monkeypatch.setattr(
        "sys.argv",
        [
            "alphaforge",
            "run-oap-mom12m-pipeline",
            "--characteristics",
            str(characteristics_path),
            "--contract",
            str(CONTRACT_FIXTURE),
            "--market-data",
            str(market_data_path),
            "--signal-output",
            str(signal_output_path),
            "--symbol",
            "AAA",
            "--initial-capital",
            "1000",
        ],
    )

    main()

    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "passed"
    assert summary["characteristics"] == str(characteristics_path)
    assert summary["contract"] == str(CONTRACT_FIXTURE)
    assert summary["market_data"] == str(market_data_path)
    assert summary["signal_output"] == str(signal_output_path)
    assert summary["symbol"] == "AAA"
    assert summary["factor_rows"] == 3
    assert summary["signal_rows"] == 3
    assert summary["signal_contract_version"] == "v0.2"
    assert summary["target_position_source_column"] == "target_weight"
    assert summary["execution_semantics"] == "signed_close_to_close_lagged"
    assert summary["equity_curve_rows"] == 3
    assert summary["trade_count"] >= 1
    assert summary["final_equity"] == pytest.approx(1300.0)

    output = pd.read_csv(signal_output_path)
    assert output.columns.tolist() == list(OAP_SIGNAL_COLUMNS)
    assert output["datetime"].tolist() == ["2024-02-01", "2024-03-01", "2024-04-01"]
    assert output["target_weight"].tolist() == [1.0, -1.0, 0.0]


def test_run_oap_mom12m_pipeline_cli_supports_cost_arguments(tmp_path, monkeypatch, capsys) -> None:
    characteristics_path = tmp_path / "mom12m.csv"
    market_data_path = tmp_path / "market.csv"
    signal_output_path = tmp_path / "signal.csv"
    _write_characteristics(characteristics_path)
    _write_market_data(market_data_path)

    monkeypatch.setattr(
        "sys.argv",
        [
            "alphaforge",
            "run-oap-mom12m-pipeline",
            "--characteristics",
            str(characteristics_path),
            "--contract",
            str(CONTRACT_FIXTURE),
            "--market-data",
            str(market_data_path),
            "--signal-output",
            str(signal_output_path),
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
    assert summary["status"] == "passed"
    assert summary["final_equity"] == pytest.approx(650.0)
