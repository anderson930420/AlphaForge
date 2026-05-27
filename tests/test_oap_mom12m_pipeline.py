from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from alphaforge.backtest import SIGNED_EXECUTION_SEMANTICS
from alphaforge.oap_mom12m_pipeline import run_oap_mom12m_pipeline_smoke
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


def _market_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "datetime": ["2024-02-01", "2024-03-01", "2024-04-01"],
            "open": [10.0, 11.0, 9.0],
            "high": [10.0, 11.0, 9.0],
            "low": [10.0, 11.0, 9.0],
            "close": [10.0, 11.0, 9.0],
            "volume": [100, 100, 100],
            "symbol": ["AAA", "AAA", "AAA"],
        }
    )


def test_oap_mom12m_pipeline_writes_signal_and_runs_signed_backtest(tmp_path: Path) -> None:
    characteristics_path = tmp_path / "mom12m.csv"
    signal_output_path = tmp_path / "signal.csv"
    _write_characteristics(characteristics_path)

    result = run_oap_mom12m_pipeline_smoke(
        characteristics_path=characteristics_path,
        contract_path=CONTRACT_FIXTURE,
        market_data=_market_data(),
        signal_output_path=signal_output_path,
        symbol="AAA",
    )

    assert result.signal_output_path == signal_output_path
    assert signal_output_path.exists()
    assert result.contract.factor["name"] == "Mom12m"
    assert result.factor_frame["factor_value"].tolist() == [0.2, -0.1, 0.0]
    assert result.signal_frame["datetime"].astype(str).tolist() == ["2024-02-01", "2024-03-01", "2024-04-01"]
    assert result.signal_frame["target_weight"].tolist() == [1.0, -1.0, 0.0]
    assert result.target_positions.tolist() == [1.0, -1.0, 0.0]
    assert result.signal_metadata["signal_contract_version"] == "v0.2"
    assert result.signal_metadata["target_position_source_column"] == "target_weight"
    assert result.equity_curve["position"].tolist() == [0.0, 1.0, -1.0]
    assert result.equity_curve["equity"].iloc[-1] == pytest.approx(1222.2222222222222)
    assert len(result.trades) >= 1


def test_oap_mom12m_pipeline_respects_signed_execution_config(tmp_path: Path) -> None:
    characteristics_path = tmp_path / "mom12m.csv"
    signal_output_path = tmp_path / "signal.csv"
    _write_characteristics(characteristics_path)

    config = BacktestConfig(
        initial_capital=500.0,
        fee_rate=0.0,
        slippage_rate=0.0,
        annualization_factor=252,
        execution_semantics=SIGNED_EXECUTION_SEMANTICS,
    )

    result = run_oap_mom12m_pipeline_smoke(
        characteristics_path=characteristics_path,
        contract_path=CONTRACT_FIXTURE,
        market_data=_market_data(),
        signal_output_path=signal_output_path,
        symbol="AAA",
        backtest_config=config,
    )

    assert result.equity_curve["equity"].iloc[0] == pytest.approx(500.0)
    assert result.equity_curve["target_position"].tolist() == [1.0, -1.0, 0.0]


def test_oap_mom12m_pipeline_rejects_non_mom12m_contract(tmp_path: Path) -> None:
    characteristics_path = tmp_path / "mom12m.csv"
    signal_output_path = tmp_path / "signal.csv"
    contract_path = tmp_path / "contract.yaml"
    _write_characteristics(characteristics_path)
    contract_path.write_text(CONTRACT_FIXTURE.read_text(encoding="utf-8").replace("name: Mom12m", "name: BM"), encoding="utf-8")

    with pytest.raises(ValueError, match="Mom12m"):
        run_oap_mom12m_pipeline_smoke(
            characteristics_path=characteristics_path,
            contract_path=contract_path,
            market_data=_market_data(),
            signal_output_path=signal_output_path,
            symbol="AAA",
        )
