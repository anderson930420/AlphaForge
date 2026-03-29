from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.visualization import build_drawdown_figure, build_equity_curve_figure, build_price_trade_figure

go = pytest.importorskip("plotly.graph_objects")


def test_build_equity_curve_figure_returns_plotly_figure() -> None:
    equity_curve = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=3, freq="D"),
            "equity": [100000.0, 101500.0, 100750.0],
        }
    )

    figure = build_equity_curve_figure(equity_curve)

    assert isinstance(figure, go.Figure)
    assert len(figure.data) == 1
    assert figure.data[0].name == "Strategy Equity"


def test_build_equity_curve_figure_requires_datetime_and_equity_columns() -> None:
    equity_curve = pd.DataFrame({"equity": [100000.0, 101000.0]})

    with pytest.raises(ValueError, match="datetime"):
        build_equity_curve_figure(equity_curve)


def test_build_drawdown_figure_returns_plotly_figure_with_expected_series() -> None:
    equity_curve = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=4, freq="D"),
            "equity": [100.0, 120.0, 90.0, 110.0],
        }
    )

    figure = build_drawdown_figure(equity_curve)

    assert isinstance(figure, go.Figure)
    assert len(figure.data) == 1
    assert figure.data[0].name == "Drawdown"
    assert list(figure.data[0].y) == [0.0, 0.0, -0.25, -0.08333333333333337]


def test_build_drawdown_figure_requires_datetime_and_equity_columns() -> None:
    equity_curve = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=2, freq="D")})

    with pytest.raises(ValueError, match="equity"):
        build_drawdown_figure(equity_curve)


def test_build_price_trade_figure_returns_close_line_with_trade_markers() -> None:
    equity_curve = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=4, freq="D"),
            "close": [100.0, 102.0, 101.0, 105.0],
        }
    )
    trades = pd.DataFrame(
        {
            "entry_time": ["2024-01-02 00:00:00"],
            "exit_time": ["2024-01-04 00:00:00"],
            "entry_price": [102.0],
            "exit_price": [105.0],
        }
    )

    figure = build_price_trade_figure(equity_curve, trades)

    assert isinstance(figure, go.Figure)
    assert [trace.name for trace in figure.data] == ["Close Price", "Buy", "Sell"]
    assert list(figure.data[1].x) == [pd.Timestamp("2024-01-02 00:00:00")]
    assert list(figure.data[1].y) == [102.0]
    assert list(figure.data[2].x) == [pd.Timestamp("2024-01-04 00:00:00")]
    assert list(figure.data[2].y) == [105.0]


def test_build_price_trade_figure_requires_close_column() -> None:
    equity_curve = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=2, freq="D")})

    with pytest.raises(ValueError, match="close"):
        build_price_trade_figure(equity_curve, pd.DataFrame())
