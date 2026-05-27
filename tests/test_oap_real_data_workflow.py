from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.oap_real_data_workflow import run_oap_mom12m_real_data_local_workflow
from alphaforge.schemas import BacktestConfig


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


def test_oap_mom12m_real_data_workflow_writes_signal_and_report(tmp_path: Path) -> None:
    characteristics_path = tmp_path / "mom12m_real.csv"
    market_data_path = tmp_path / "market.csv"
    signal_output_path = tmp_path / "signal.csv"
    report_output_path = tmp_path / "report.json"
    _write_characteristics(characteristics_path)
    _write_market_data(market_data_path)

    result = run_oap_mom12m_real_data_local_workflow(
        characteristics_path=characteristics_path,
        contract_path=CONTRACT_FIXTURE,
        market_data_path=market_data_path,
        signal_output_path=signal_output_path,
        report_output_path=report_output_path,
        symbol="AAA",
    )

    assert signal_output_path.exists()
    assert report_output_path.exists()
    assert result.report_output_path == report_output_path
    assert result.summary["status"] == "passed"
    assert result.summary["workflow"] == "oap_mom12m_real_data_local"
    assert result.summary["inputs"]["characteristics"] == str(characteristics_path)
    assert result.summary["inputs"]["contract"] == str(CONTRACT_FIXTURE)
    assert result.summary["inputs"]["market_data"] == str(market_data_path)
    assert result.summary["inputs"]["symbol"] == "AAA"
    assert result.summary["outputs"]["signal_output"] == str(signal_output_path)
    assert result.summary["contract"]["factor_name"] == "Mom12m"
    assert result.summary["contract"]["decision_rule_type"] == "threshold"
    assert result.summary["contract"]["target_weight_mode"] == "signed_unit"
    assert result.summary["factor_frame"]["row_count"] == 3
    assert result.summary["factor_frame"]["symbol_count"] == 1
    assert result.summary["factor_frame"]["date_min"] == "2024-01-31"
    assert result.summary["factor_frame"]["date_max"] == "2024-03-31"
    assert result.summary["factor_frame"]["available_at_min"] == "2024-02-01"
    assert result.summary["factor_frame"]["available_at_max"] == "2024-04-01"
    assert result.summary["factor_frame"]["missing_factor_value_count"] == 0
    assert result.summary["factor_frame"]["factor_value_min"] == pytest.approx(-0.1)
    assert result.summary["factor_frame"]["factor_value_max"] == pytest.approx(0.2)
    assert result.summary["signal_frame"]["row_count"] == 3
    assert result.summary["signal_frame"]["direction_counts"] == {"-1": 1, "0": 1, "1": 1}
    assert result.summary["signal_frame"]["target_weight_counts"] == {"-1.0": 1, "0.0": 1, "1.0": 1}
    assert result.summary["backtest"]["execution_semantics"] == "signed_close_to_close_lagged"
    assert result.summary["backtest"]["initial_capital"] == pytest.approx(1000.0)
    assert result.summary["backtest"]["final_equity"] == pytest.approx(1300.0)
    assert result.summary["signal_metadata"]["signal_contract_version"] == "v0.2"
    assert result.summary["signal_metadata"]["target_position_source_column"] == "target_weight"

    persisted = json.loads(report_output_path.read_text(encoding="utf-8"))
    assert persisted == result.summary


def test_oap_mom12m_real_data_workflow_accepts_custom_backtest_config(tmp_path: Path) -> None:
    characteristics_path = tmp_path / "mom12m_real.csv"
    market_data_path = tmp_path / "market.csv"
    signal_output_path = tmp_path / "signal.csv"
    _write_characteristics(characteristics_path)
    _write_market_data(market_data_path)

    result = run_oap_mom12m_real_data_local_workflow(
        characteristics_path=characteristics_path,
        contract_path=CONTRACT_FIXTURE,
        market_data_path=market_data_path,
        signal_output_path=signal_output_path,
        symbol="AAA",
        backtest_config=BacktestConfig(
            initial_capital=500.0,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
            execution_semantics="signed_close_to_close_lagged",
        ),
    )

    assert result.report_output_path is None
    assert result.summary["backtest"]["initial_capital"] == pytest.approx(500.0)
    assert result.summary["backtest"]["final_equity"] == pytest.approx(650.0)
