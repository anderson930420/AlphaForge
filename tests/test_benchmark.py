from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.benchmark import build_buy_and_hold_equity_curve, normalize_benchmark_summary, summarize_buy_and_hold


def test_build_buy_and_hold_equity_curve_tracks_close_series_from_initial_capital() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=3, freq="D"),
            "close": [100.0, 110.0, 105.0],
        }
    )

    benchmark_curve = build_buy_and_hold_equity_curve(market_data, initial_capital=1000.0)

    assert benchmark_curve["equity"].tolist() == [1000.0, 1100.0, 1050.0]


def test_summarize_buy_and_hold_returns_total_return_and_max_drawdown() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=4, freq="D"),
            "close": [100.0, 120.0, 90.0, 110.0],
        }
    )

    summary = summarize_buy_and_hold(market_data, initial_capital=1000.0)

    assert summary["total_return"] == pytest.approx(0.1)
    assert summary["max_drawdown"] == pytest.approx(-0.25)


def test_build_buy_and_hold_equity_curve_requires_close_column() -> None:
    market_data = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=2, freq="D")})

    with pytest.raises(ValueError, match="close"):
        build_buy_and_hold_equity_curve(market_data, initial_capital=1000.0)


def test_normalize_benchmark_summary_coerces_partial_payload_to_canonical_shape() -> None:
    summary = normalize_benchmark_summary({"total_return": "0.12"})

    assert summary == {"total_return": 0.12, "max_drawdown": 0.0}
