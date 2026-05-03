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

    with pytest.raises(ValueError, match="duplicate datetime for the same symbol fails"):
        load_custom_signal_positions(signal_file, market_data)


def test_missing_signal_date_relative_to_market_data_fails(tmp_path: Path) -> None:
    market_data = _build_market_data()
    signal_file = _write_signal_csv(
        tmp_path,
        pd.DataFrame(
            {
                "datetime": ["2024-01-01", "2024-01-03"],
                "available_at": ["2023-12-31", "2024-01-02"],
                "symbol": ["2330", "2330"],
                "signal_name": ["demo_signal"] * 2,
                "signal_value": [1, 1],
                "signal_binary": [0, 1],
                "source": ["SignalForge"] * 2,
            }
        ),
    )

    with pytest.raises(ValueError, match="signal dates must align with market data dates"):
        load_custom_signal_positions(signal_file, market_data)


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


def test_no_signalforge_import_exists() -> None:
    source = Path(__file__).resolve().parents[1] / "src" / "alphaforge" / "custom_signal.py"
    text = source.read_text(encoding="utf-8")

    assert "SignalForge" not in text
