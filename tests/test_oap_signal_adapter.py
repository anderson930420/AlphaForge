from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.custom_signal import load_custom_signal_positions
from alphaforge.oap_factor_contract import load_oap_factor_contract
from alphaforge.oap_loader import normalize_oap_factor_frame
from alphaforge.oap_signal_adapter import (
    OAPSignalAdapterError,
    build_oap_signal_frame_from_factor_frame,
)
from alphaforge.open_asset_pricing import OAP_SIGNAL_COLUMNS


CONTRACT_FIXTURE = Path("tests/fixtures/oap_factor_contracts/mom12m_threshold.yaml")


def _contract():
    return load_oap_factor_contract(CONTRACT_FIXTURE)


def _raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2024-01-31", "2024-01-31", "2024-01-31"],
            "permno": ["10001", "10002", "10003"],
            "symbol": ["AAA", "BBB", "CCC"],
            "Mom12m": [0.12, -0.05, 0.0],
        }
    )


def _factor_frame() -> pd.DataFrame:
    return normalize_oap_factor_frame(_raw_frame(), _contract())


def test_oap_signal_adapter_maps_threshold_factor_values_to_v02_signal_rows() -> None:
    signal_frame = build_oap_signal_frame_from_factor_frame(_factor_frame(), _contract())

    assert signal_frame.columns.tolist() == list(OAP_SIGNAL_COLUMNS)
    assert signal_frame["signal_name"].unique().tolist() == ["oap_Mom12m"]
    assert signal_frame["source"].unique().tolist() == ["open_asset_pricing:jkp"]

    by_symbol = signal_frame.set_index("symbol")
    assert by_symbol.loc["AAA", "score"] == pytest.approx(0.12)
    assert by_symbol.loc["AAA", "direction"] == 1
    assert by_symbol.loc["AAA", "target_weight"] == pytest.approx(1.0)
    assert by_symbol.loc["BBB", "direction"] == -1
    assert by_symbol.loc["BBB", "target_weight"] == pytest.approx(-1.0)
    assert by_symbol.loc["CCC", "direction"] == 0
    assert by_symbol.loc["CCC", "target_weight"] == pytest.approx(0.0)


def test_oap_signal_adapter_supports_signal_name_override() -> None:
    signal_frame = build_oap_signal_frame_from_factor_frame(
        _factor_frame(),
        _contract(),
        signal_name="custom_mom12m",
    )

    assert signal_frame["signal_name"].unique().tolist() == ["custom_mom12m"]


def test_oap_signal_adapter_uses_contract_signed_unit_weights() -> None:
    contract = _contract()
    weighted = replace(
        contract,
        weighting={**contract.weighting, "long_weight": 0.5, "short_weight": -0.25},
    )

    signal_frame = build_oap_signal_frame_from_factor_frame(_factor_frame(), weighted)
    by_symbol = signal_frame.set_index("symbol")

    assert by_symbol.loc["AAA", "target_weight"] == pytest.approx(0.5)
    assert by_symbol.loc["BBB", "target_weight"] == pytest.approx(-0.25)
    assert by_symbol.loc["CCC", "target_weight"] == pytest.approx(0.0)


def test_oap_signal_adapter_rejects_missing_required_factor_columns() -> None:
    with pytest.raises(OAPSignalAdapterError, match="Missing required normalized OAP factor columns"):
        build_oap_signal_frame_from_factor_frame(_factor_frame().drop(columns=["factor_value"]), _contract())


def test_oap_signal_adapter_rejects_wrong_factor_name() -> None:
    factor_frame = _factor_frame()
    factor_frame["factor_name"] = "BM"

    with pytest.raises(OAPSignalAdapterError, match="factor_name"):
        build_oap_signal_frame_from_factor_frame(factor_frame, _contract())


def test_oap_signal_adapter_rejects_duplicate_datetime_symbol_factor_rows() -> None:
    factor_frame = pd.concat([_factor_frame(), _factor_frame().iloc[[0]]], ignore_index=True)

    with pytest.raises(OAPSignalAdapterError, match="duplicate datetime-symbol-factor_name"):
        build_oap_signal_frame_from_factor_frame(factor_frame, _contract())


def test_oap_signal_adapter_rejects_unsupported_decision_rule_type() -> None:
    contract = _contract()
    unsupported = replace(contract, decision_rule={**contract.decision_rule, "type": "cross_sectional_rank"})

    with pytest.raises(OAPSignalAdapterError, match="Unsupported decision_rule.type"):
        build_oap_signal_frame_from_factor_frame(_factor_frame(), unsupported)


def test_oap_signal_adapter_rejects_unsupported_weighting_mode() -> None:
    contract = _contract()
    unsupported = replace(contract, weighting={**contract.weighting, "target_weight_mode": "gross_normalized"})

    with pytest.raises(OAPSignalAdapterError, match="Unsupported weighting.target_weight_mode"):
        build_oap_signal_frame_from_factor_frame(_factor_frame(), unsupported)


def test_oap_signal_adapter_output_can_be_consumed_by_custom_signal_loader(tmp_path: Path) -> None:
    signal_frame = build_oap_signal_frame_from_factor_frame(_factor_frame(), _contract())
    single_symbol_signal = signal_frame.loc[signal_frame["symbol"].eq("AAA")].copy()
    signal_path = tmp_path / "signal.csv"
    single_symbol_signal.to_csv(signal_path, index=False)

    market_data = pd.DataFrame(
        {
            "datetime": ["2024-01-31"],
            "open": [10.0],
            "high": [10.0],
            "low": [10.0],
            "close": [10.0],
            "volume": [100],
            "symbol": ["AAA"],
        }
    )

    target_position, metadata = load_custom_signal_positions(signal_path, market_data)

    assert target_position.tolist() == [1.0]
    assert metadata["signal_contract_version"] == "v0.2"
    assert metadata["target_position_source_column"] == "target_weight"
}
