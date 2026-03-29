from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest
import requests

from alphaforge.twse_client import (
    TwseFetchRequest,
    fetch_stock_day_history,
    _iter_month_starts,
    _normalize_stock_day_payload,
    save_stock_day_history,
)


def test_iter_month_starts_includes_each_month_inclusive() -> None:
    assert _iter_month_starts("2024-01", "2024-03") == ["20240101", "20240201", "20240301"]


def test_iter_month_starts_rejects_reversed_range() -> None:
    with pytest.raises(ValueError, match="start_month"):
        _iter_month_starts("2024-03", "2024-01")


def test_normalize_stock_day_payload_to_standard_ohlcv_frame() -> None:
    payload = {
        "stat": "OK",
        "data": [
            ["113/03/01", "24,167,721", "16,699,995,060", "697.00", "697.00", "688.00", "689.00", "-1.00"],
            ["113/03/04", "97,210,112", "69,868,348,694", "714.00", "725.00", "711.00", "725.00", "+36.00"],
        ],
    }

    frame = _normalize_stock_day_payload(payload)

    assert frame.columns.tolist() == ["datetime", "open", "high", "low", "close", "volume"]
    assert frame.iloc[0].to_dict() == {
        "datetime": "2024-03-01",
        "open": 697.0,
        "high": 697.0,
        "low": 688.0,
        "close": 689.0,
        "volume": 24167721.0,
    }


def test_save_stock_day_history_writes_csv(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        [
            {
                "datetime": "2024-03-01",
                "open": 697.0,
                "high": 697.0,
                "low": 688.0,
                "close": 689.0,
                "volume": 24167721.0,
            }
        ]
    )
    output_path = tmp_path / "twse" / "2330.csv"

    save_stock_day_history(frame, output_path)

    loaded = pd.read_csv(output_path)
    assert loaded.shape == (1, 6)
    assert loaded.iloc[0]["datetime"] == "2024-03-01"


def test_fetch_stock_day_history_falls_back_after_ssl_error() -> None:
    payload = {
        "stat": "OK",
        "data": [
            ["113/03/01", "24,167,721", "16,699,995,060", "697.00", "697.00", "688.00", "689.00", "-1.00"]
        ],
    }
    success_response = Mock()
    success_response.json.return_value = payload
    success_response.raise_for_status.return_value = None

    with patch(
        "alphaforge.twse_client.requests.get",
        side_effect=[requests.exceptions.SSLError("ssl"), success_response],
    ) as mock_get:
        frame = fetch_stock_day_history(TwseFetchRequest(stock_no="2330", start_month="2024-03", end_month="2024-03"))

    assert len(frame) == 1
    assert mock_get.call_count == 2
    assert mock_get.call_args_list[0].kwargs["verify"] is not False
    assert mock_get.call_args_list[1].kwargs["verify"] is False
