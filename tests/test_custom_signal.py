from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from alphaforge.custom_signal import load_custom_signal_positions


def _build_market_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "open": [10.0, 11.0, 12.0],
            "high": [10.5, 11.5, 12.5],
            "low": [9.5, 10.5, 11.5],
            "close": [10.0, 11.0, 12.0],
            "volume": [100.0, 110.0, 120.0],
            "symbol": ["2330", "2330", "2330"],
        }
    )


def _write_signal_csv(tmp_path: Path, frame: pd.DataFrame) -> Path:
    path = tmp_path / "signal.csv"
    frame.to_csv(path, index=False)
    return path


def test_load_custom_signal_positions_returns_aligned_target_positions(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": ["2023-12-31", "2024-01-01", "2024-01-02"],
                "symbol": ["2330", "2330", "2330"],
                "signal_name": ["demo_signal"] * 3,
                "signal_value": [999, -999, 123],
                "signal_binary": [0, 1, 0],
                "source": ["SignalForge"] * 3,
            }
        ),
    )

    target_position, metadata = load_custom_signal_positions(signal_file, market_data)

    expected = pd.Series([0.0, 1.0, 0.0], index=market_data.index, name="target_position")
    pd.testing.assert_series_equal(target_position, expected)
    assert metadata == {
        "symbol": "2330",
        "signal_row_count": 3,
        "missing_signal_policy": "flat",
        "signal_contract_version": "v0.1",
        "target_position_source_column": "signal_binary",
        "signal_name": "demo_signal",
        "source": "SignalForge",
    }


def test_signal_binary_maps_to_float_target_position(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": ["2023-12-31", "2024-01-01", "2024-01-02"],
                "symbol": ["2330", "2330", "2330"],
                "signal_name": ["demo_signal"] * 3,
                "signal_value": [1, 1, 1],
                "signal_binary": [0, 1, 1],
                "source": ["SignalForge"] * 3,
            }
        ),
    )

    target_position, _ = load_custom_signal_positions(signal_file, market_data, symbol="2330")

    assert target_position.dtype == float
    assert target_position.tolist() == [0.0, 1.0, 1.0]


def test_v02_target_weight_signal_maps_to_float_target_position(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": ["2023-12-31", "2024-01-01", "2024-01-02"],
                "symbol": ["2330", "2330", "2330"],
                "signal_name": ["demo_v02"] * 3,
                "score": [0.3, 0.0, 0.8],
                "direction": [1, 0, 1],
                "target_weight": [0.25, 0.0, 0.75],
                "source": ["SignalForge"] * 3,
            }
        ),
    )

    target_position, metadata = load_custom_signal_positions(signal_file, market_data)

    assert target_position.tolist() == [0.25, 0.0, 0.75]
    assert metadata["signal_contract_version"] == "v0.2"
    assert metadata["target_position_source_column"] == "target_weight"
    assert metadata["signal_name"] == "demo_v02"


def test_v02_missing_signal_dates_default_to_flat(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-03"],
                "available_at": ["2024-01-02"],
                "symbol": ["2330"],
                "signal_name": ["demo_v02"],
                "score": [0.8],
                "direction": [1],
                "target_weight": [0.5],
                "source": ["SignalForge"],
            }
        ),
    )

    target_position, metadata = load_custom_signal_positions(signal_file, market_data)

    assert target_position.tolist() == [0.0, 0.0, 0.5]
    assert metadata["missing_signal_policy"] == "flat"
    assert metadata["signal_contract_version"] == "v0.2"


def test_v02_negative_target_weight_fails_until_short_runtime_exists(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01"],
                "available_at": ["2023-12-31"],
                "symbol": ["2330"],
                "signal_name": ["demo_v02"],
                "score": [-0.8],
                "direction": [-1],
                "target_weight": [-0.25],
                "source": ["SignalForge"],
            }
        ),
    )

    with pytest.raises(ValueError, match="negative target_weight is not supported"):
        load_custom_signal_positions(signal_file, market_data)


def test_v02_target_weight_above_one_fails_for_current_runtime(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01"],
                "available_at": ["2023-12-31"],
                "symbol": ["2330"],
                "signal_name": ["demo_v02"],
                "score": [1.2],
                "direction": [1],
                "target_weight": [1.1],
                "source": ["SignalForge"],
            }
        ),
    )

    with pytest.raises(ValueError, match="target_weight must be less than or equal to 1.0"):
        load_custom_signal_positions(signal_file, market_data)


def test_v02_non_ternary_direction_fails(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01"],
                "available_at": ["2023-12-31"],
                "symbol": ["2330"],
                "signal_name": ["demo_v02"],
                "score": [0.3],
                "direction": [2],
                "target_weight": [0.25],
                "source": ["SignalForge"],
            }
        ),
    )

    with pytest.raises(ValueError, match="direction must be ternary"):
        load_custom_signal_positions(signal_file, market_data)


def test_v02_missing_required_column_fails_with_contract_version(tmp_path: Path) -> None:
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01"],
                "available_at": ["2023-12-31"],
                "symbol": ["2330"],
                "signal_name": ["demo_v02"],
                "score": [0.3],
                "target_weight": [0.25],
                "source": ["SignalForge"],
            }
        ),
    )

    with pytest.raises(ValueError, match=r"Missing required v0.2 signal columns: \['direction'\]"):
        load_custom_signal_positions(signal_file, _build_market_data())


@pytest.mark.parametrize(
    "signal_datetime",
    [
        "2025-01-02T00:00:00+08:00",
        "2025-01-02T00:00:00Z",
        "2025-01-02 09:30:00+08:00",
    ],
)
def test_signal_datetime_uses_declared_calendar_date_for_daily_alignment(
    tmp_path: Path,
    signal_datetime: str,
) -> None:
    market_data = pd.DataFrame(
        {
            "datetime": ["2025-01-02"],
            "open": [10.0],
            "high": [10.5],
            "low": [9.5],
            "close": [10.0],
            "volume": [100.0],
            "symbol": ["2330"],
        }
    )
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": [signal_datetime],
                "available_at": ["2025-01-01T23:59:00+00:00"],
                "symbol": ["2330"],
                "signal_name": ["demo_signal"],
                "signal_value": [999],
                "signal_binary": [1],
                "source": ["SignalForge"],
            }
        ),
    )

    target_position, _ = load_custom_signal_positions(signal_file, market_data)

    expected = pd.Series([1.0], index=market_data.index, name="target_position")
    pd.testing.assert_series_equal(target_position, expected)


def test_offset_available_at_on_same_date_passes_daily_alignment(tmp_path: Path) -> None:
    market_data = pd.DataFrame(
        {
            "datetime": ["2025-01-02"],
            "open": [10.0],
            "high": [10.5],
            "low": [9.5],
            "close": [10.0],
            "volume": [100.0],
            "symbol": ["2330"],
        }
    )
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2025-01-02"],
                "available_at": ["2025-01-02T00:00:00+08:00"],
                "symbol": ["2330"],
                "signal_name": ["demo_signal"],
                "signal_value": [1],
                "signal_binary": [1],
                "source": ["SignalForge"],
            }
        ),
    )

    target_position, _ = load_custom_signal_positions(signal_file, market_data)

    assert target_position.tolist() == [1.0]


def test_intraday_available_at_ordering_on_same_date_is_not_validated(tmp_path: Path) -> None:
    market_data = pd.DataFrame(
        {
            "datetime": ["2025-01-02"],
            "open": [10.0],
            "high": [10.5],
            "low": [9.5],
            "close": [10.0],
            "volume": [100.0],
            "symbol": ["2330"],
        }
    )
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2025-01-02T09:30:00+08:00"],
                "available_at": ["2025-01-02T23:00:00+08:00"],
                "symbol": ["2330"],
                "signal_name": ["demo_signal"],
                "signal_value": [1],
                "signal_binary": [1],
                "source": ["SignalForge"],
            }
        ),
    )

    target_position, _ = load_custom_signal_positions(signal_file, market_data)

    assert target_position.tolist() == [1.0]


def test_signal_value_is_ignored_for_execution(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": ["2023-12-31", "2024-01-01", "2024-01-02"],
                "symbol": ["2330", "2330", "2330"],
                "signal_name": ["demo_signal"] * 3,
                "signal_value": [999999, -888888, 123456],
                "signal_binary": [1, 0, 1],
                "source": ["SignalForge"] * 3,
            }
        ),
    )

    target_position, _ = load_custom_signal_positions(signal_file, market_data)

    assert target_position.tolist() == [1.0, 0.0, 1.0]


@pytest.mark.parametrize(
    "column, value, message",
    [
        ("datetime", None, "datetime is required"),
        ("available_at", None, "available_at is required"),
        ("symbol", None, "symbol is required"),
        ("signal_binary", None, "signal_binary is required"),
    ],
)
def test_missing_required_signal_fields_fail(tmp_path: Path, column: str, value: object, message: str) -> None:
    market_data = _build_market_data()
    frame = pd.DataFrame(
        {
            "datetime": ["2024-01-01"],
            "available_at": ["2023-12-31"],
            "symbol": ["2330"],
            "signal_name": ["demo_signal"],
            "signal_value": [1],
            "signal_binary": [1],
            "source": ["SignalForge"],
        }
    )
    frame.loc[0, column] = value
    signal_file = _write_signal_csv(tmp_path, frame)

    with pytest.raises(ValueError, match=message):
        load_custom_signal_positions(signal_file, market_data)


def test_unparseable_signal_datetime_fails_clearly(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["not-a-date"],
                "available_at": ["2024-01-01"],
                "symbol": ["2330"],
                "signal_name": ["demo_signal"],
                "signal_value": [1],
                "signal_binary": [1],
                "source": ["SignalForge"],
            }
        ),
    )

    with pytest.raises(ValueError, match="Could not parse datetime value 'not-a-date'"):
        load_custom_signal_positions(signal_file, market_data)


def test_missing_signal_symbol_fails_clearly(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": ["2023-12-31", "2024-01-01", "2024-01-02"],
                "symbol": [None, None, None],
                "signal_name": ["demo_signal"] * 3,
                "signal_value": [1, 1, 1],
                "signal_binary": [1, 0, 1],
                "source": ["SignalForge"] * 3,
            }
        ),
    )

    with pytest.raises(ValueError, match="symbol is required"):
        load_custom_signal_positions(signal_file, market_data)


def test_multiple_signal_symbols_fail_clearly(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": ["2023-12-31", "2024-01-01", "2024-01-02"],
                "symbol": ["2330", "2317", "2330"],
                "signal_name": ["demo_signal"] * 3,
                "signal_value": [1, 1, 1],
                "signal_binary": [1, 0, 1],
                "source": ["SignalForge"] * 3,
            }
        ),
    )

    with pytest.raises(ValueError, match="signal.csv must contain exactly one symbol for custom_signal"):
        load_custom_signal_positions(signal_file, market_data)


def test_multiple_market_symbols_fail_clearly(tmp_path: Path) -> None:
    market_data = _build_market_data()
    market_data.loc[1, "symbol"] = "2317"
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": ["2023-12-31", "2024-01-01", "2024-01-02"],
                "symbol": ["2330", "2330", "2330"],
                "signal_name": ["demo_signal"] * 3,
                "signal_value": [1, 1, 1],
                "signal_binary": [1, 0, 1],
                "source": ["SignalForge"] * 3,
            }
        ),
    )

    with pytest.raises(ValueError, match="market_data must contain exactly one symbol for custom_signal"):
        load_custom_signal_positions(signal_file, market_data)


def test_single_signal_symbol_works_without_market_symbol_column(tmp_path: Path) -> None:
    market_data = _build_market_data().drop(columns=["symbol"])
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": ["2023-12-31", "2024-01-01", "2024-01-02"],
                "symbol": ["2330", "2330", "2330"],
                "signal_name": ["demo_signal"] * 3,
                "signal_value": [1, 1, 1],
                "signal_binary": [1, 0, 1],
                "source": ["SignalForge"] * 3,
            }
        ),
    )

    target_position, metadata = load_custom_signal_positions(signal_file, market_data)

    assert target_position.tolist() == [1.0, 0.0, 1.0]
    assert metadata["symbol"] == "2330"


def test_non_binary_signal_binary_fails(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": ["2023-12-31", "2024-01-01", "2024-01-02"],
                "symbol": ["2330", "2330", "2330"],
                "signal_name": ["demo_signal"] * 3,
                "signal_value": [1, 1, 1],
                "signal_binary": [0, 2, 1],
                "source": ["SignalForge"] * 3,
            }
        ),
    )

    with pytest.raises(ValueError, match="signal_binary must be binary: 0 or 1"):
        load_custom_signal_positions(signal_file, market_data)


def test_available_at_after_datetime_fails(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": ["2024-01-01", "2024-01-03", "2024-01-02"],
                "symbol": ["2330", "2330", "2330"],
                "signal_name": ["demo_signal"] * 3,
                "signal_value": [1, 1, 1],
                "signal_binary": [0, 1, 0],
                "source": ["SignalForge"] * 3,
            }
        ),
    )

    with pytest.raises(ValueError, match="available_at must be less than or equal to datetime"):
        load_custom_signal_positions(signal_file, market_data)


def test_available_at_declared_calendar_date_after_datetime_fails(tmp_path: Path) -> None:
    market_data = pd.DataFrame(
        {
            "datetime": ["2025-01-02"],
            "open": [10.0],
            "high": [10.5],
            "low": [9.5],
            "close": [10.0],
            "volume": [100.0],
            "symbol": ["2330"],
        }
    )
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2025-01-02T23:00:00+08:00"],
                "available_at": ["2025-01-03T00:00:00+08:00"],
                "symbol": ["2330"],
                "signal_name": ["demo_signal"],
                "signal_value": [1],
                "signal_binary": [1],
                "source": ["SignalForge"],
            }
        ),
    )

    with pytest.raises(ValueError, match="available_at must be less than or equal to datetime"):
        load_custom_signal_positions(signal_file, market_data)


def test_duplicate_datetime_for_same_symbol_fails(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-01", "2024-01-03"],
                "available_at": ["2023-12-31", "2023-12-31", "2024-01-02"],
                "symbol": ["2330", "2330", "2330"],
                "signal_name": ["demo_signal"] * 3,
                "signal_value": [1, 1, 1],
                "signal_binary": [0, 1, 0],
                "source": ["SignalForge"] * 3,
            }
        ),
    )

    with pytest.raises(ValueError, match="duplicate datetime-symbol-signal_name rows are not allowed"):
        load_custom_signal_positions(signal_file, market_data)


def test_missing_signal_dates_default_to_flat_and_do_not_look_ahead(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-03"],
                "available_at": ["2024-01-02"],
                "symbol": ["2330"],
                "signal_name": ["demo_signal"],
                "signal_value": [1],
                "signal_binary": [1],
                "source": ["SignalForge"],
            }
        ),
    )

    target_position, metadata = load_custom_signal_positions(signal_file, market_data)

    assert target_position.tolist() == [0.0, 0.0, 1.0]
    assert metadata["missing_signal_policy"] == "flat"


def test_utc_signal_missing_dates_default_to_flat(tmp_path: Path) -> None:
    market_data = pd.DataFrame(
        {
            "datetime": ["2025-01-02", "2025-01-03"],
            "open": [10.0, 11.0],
            "high": [10.5, 11.5],
            "low": [9.5, 10.5],
            "close": [10.0, 11.0],
            "volume": [100.0, 110.0],
            "symbol": ["2330", "2330"],
        }
    )
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2025-01-03T00:00:00+00:00"],
                "available_at": ["2025-01-02T00:00:00+00:00"],
                "symbol": ["2330"],
                "signal_name": ["demo_signal"],
                "signal_value": [1],
                "signal_binary": [1],
                "source": ["SignalForge"],
            }
        ),
    )

    target_position, metadata = load_custom_signal_positions(signal_file, market_data)

    assert target_position.tolist() == [0.0, 1.0]
    assert metadata["missing_signal_policy"] == "flat"


def test_extra_signal_date_not_in_market_data_fails(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
                "available_at": ["2023-12-31", "2024-01-01", "2024-01-02", "2024-01-03"],
                "symbol": ["2330", "2330", "2330", "2330"],
                "signal_name": ["demo_signal"] * 4,
                "signal_value": [1, 1, 1, 1],
                "signal_binary": [0, 1, 0, 1],
                "source": ["SignalForge"] * 4,
            }
        ),
    )

    with pytest.raises(ValueError, match="signal dates must align with market data dates"):
        load_custom_signal_positions(signal_file, market_data)


def test_utc_extra_signal_date_not_in_market_data_fails(tmp_path: Path) -> None:
    market_data = pd.DataFrame(
        {
            "datetime": ["2025-01-02"],
            "open": [10.0],
            "high": [10.5],
            "low": [9.5],
            "close": [10.0],
            "volume": [100.0],
            "symbol": ["2330"],
        }
    )
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2025-01-02T00:00:00+00:00", "2025-01-03T00:00:00+00:00"],
                "available_at": ["2025-01-01T00:00:00+00:00", "2025-01-02T00:00:00+00:00"],
                "symbol": ["2330", "2330"],
                "signal_name": ["demo_signal", "demo_signal"],
                "signal_value": [1, 1],
                "signal_binary": [1, 0],
                "source": ["SignalForge", "SignalForge"],
            }
        ),
    )

    with pytest.raises(ValueError, match="signal dates must align with market data dates"):
        load_custom_signal_positions(signal_file, market_data)


def test_multiple_signal_names_require_explicit_selection(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": [
                    "2023-12-31",
                    "2024-01-01",
                    "2024-01-02",
                    "2023-12-31",
                    "2024-01-01",
                    "2024-01-02",
                ],
                "symbol": ["2330"] * 6,
                "signal_name": ["alpha"] * 3 + ["beta"] * 3,
                "signal_value": [10, 11, 12, 20, 21, 22],
                "signal_binary": [1, 0, 1, 0, 1, 0],
                "source": ["SignalForge"] * 6,
            }
        ),
    )

    with pytest.raises(ValueError, match="multiple signal_name values"):
        load_custom_signal_positions(signal_file, market_data)


def test_explicit_signal_name_selection_filters_multi_signal_file(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": [
                    "2023-12-31",
                    "2024-01-01",
                    "2024-01-02",
                    "2023-12-31",
                    "2024-01-01",
                    "2024-01-02",
                ],
                "symbol": ["2330"] * 6,
                "signal_name": ["alpha"] * 3 + ["beta"] * 3,
                "signal_value": [10, 11, 12, 20, 21, 22],
                "signal_binary": [1, 0, 1, 0, 1, 0],
                "source": ["SignalForge"] * 6,
            }
        ),
    )

    target_position, metadata = load_custom_signal_positions(signal_file, market_data, signal_name="beta")

    assert target_position.tolist() == [0.0, 1.0, 0.0]
    assert metadata["signal_name"] == "beta"


def test_metadata_preserves_signal_name_source_and_symbol_when_unambiguous(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": ["2023-12-31", "2024-01-01", "2024-01-02"],
                "symbol": ["2330", "2330", "2330"],
                "signal_name": ["my_signal"] * 3,
                "signal_value": [10, 11, 12],
                "signal_binary": [1, 0, 1],
                "source": ["SignalForge"] * 3,
            }
        ),
    )

    _, metadata = load_custom_signal_positions(signal_file, market_data)

    assert metadata["symbol"] == "2330"
    assert metadata["signal_name"] == "my_signal"
    assert metadata["source"] == "SignalForge"


def test_metadata_omits_source_when_ambiguous(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "available_at": ["2023-12-31", "2024-01-01", "2024-01-02"],
                "symbol": ["2330", "2330", "2330"],
                "signal_name": ["my_signal"] * 3,
                "signal_value": [10, 11, 12],
                "signal_binary": [1, 0, 1],
                "source": ["SignalForge", "manual", "SignalForge"],
            }
        ),
    )

    _, metadata = load_custom_signal_positions(signal_file, market_data)

    assert "source" not in metadata


def test_no_signalforge_import_exists() -> None:
    source = Path(__file__).resolve().parents[1] / "src" / "alphaforge" / "custom_signal.py"
    text = source.read_text(encoding="utf-8")

    assert "SignalForge" not in text
