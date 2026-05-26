from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.custom_signal import load_custom_signal_positions
from alphaforge.open_asset_pricing import (
    OAP_SIGNAL_COLUMNS,
    OAPQuantilePolicy,
    build_oap_v02_signal_frame,
)


def _make_characteristics() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2024-01-31"] * 5,
            "permno": ["A", "B", "C", "D", "E"],
            "BM": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )


def test_oap_adapter_builds_v02_signal_frame_from_characteristic_scores() -> None:
    signal_frame = build_oap_v02_signal_frame(
        _make_characteristics(),
        characteristic="BM",
        asset_id_col="permno",
    )

    assert signal_frame.columns.tolist() == list(OAP_SIGNAL_COLUMNS)
    assert signal_frame["signal_name"].unique().tolist() == ["oap_BM"]
    assert signal_frame["source"].unique().tolist() == ["OpenAssetPricing"]

    by_symbol = signal_frame.set_index("symbol")
    assert by_symbol.loc["A", "direction"] == -1
    assert by_symbol.loc["A", "target_weight"] == pytest.approx(-1.0)
    assert by_symbol.loc["E", "direction"] == 1
    assert by_symbol.loc["E", "target_weight"] == pytest.approx(1.0)
    assert by_symbol.loc["C", "direction"] == 0
    assert by_symbol.loc["C", "target_weight"] == pytest.approx(0.0)


def test_oap_adapter_supports_fractional_long_short_leg_weights() -> None:
    signal_frame = build_oap_v02_signal_frame(
        _make_characteristics(),
        characteristic="BM",
        asset_id_col="permno",
        policy=OAPQuantilePolicy(
            long_quantile=0.6,
            short_quantile=0.4,
            gross_long_weight=0.5,
            gross_short_weight=-0.5,
        ),
    )

    assert signal_frame.loc[signal_frame["direction"].eq(1), "target_weight"].sum() == pytest.approx(0.5)
    assert signal_frame.loc[signal_frame["direction"].eq(-1), "target_weight"].sum() == pytest.approx(-0.5)


def test_oap_adapter_can_invert_score() -> None:
    signal_frame = build_oap_v02_signal_frame(
        _make_characteristics(),
        characteristic="BM",
        asset_id_col="permno",
        invert_score=True,
    )

    by_symbol = signal_frame.set_index("symbol")
    assert by_symbol.loc["A", "direction"] == 1
    assert by_symbol.loc["E", "direction"] == -1


def test_oap_adapter_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="Missing required Open Asset Pricing columns"):
        build_oap_v02_signal_frame(pd.DataFrame({"date": ["2024-01-31"], "BM": [1.0]}), characteristic="BM")


def test_oap_adapter_rejects_duplicate_date_symbol_rows() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2024-01-31", "2024-01-31"],
            "asset_id": ["A", "A"],
            "BM": [1.0, 2.0],
        }
    )

    with pytest.raises(ValueError, match="duplicate datetime-symbol"):
        build_oap_v02_signal_frame(frame, characteristic="BM")


def test_oap_adapter_rejects_invalid_quantile_policy() -> None:
    with pytest.raises(ValueError, match="short_quantile"):
        OAPQuantilePolicy(long_quantile=0.2, short_quantile=0.8)


def test_oap_adapter_output_can_be_consumed_after_filtering_single_symbol(tmp_path) -> None:
    signal_frame = build_oap_v02_signal_frame(
        _make_characteristics(),
        characteristic="BM",
        asset_id_col="permno",
    )
    single_symbol_signal = signal_frame.loc[signal_frame["symbol"].eq("E")].copy()
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
            "symbol": ["E"],
        }
    )

    target_position, metadata = load_custom_signal_positions(signal_path, market_data)

    assert target_position.tolist() == [1.0]
    assert metadata["signal_contract_version"] == "v0.2"
    assert metadata["target_position_source_column"] == "target_weight"
