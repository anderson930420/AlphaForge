from __future__ import annotations

"""Figure-building interfaces for AlphaForge experiment outputs.

This module is the single place for turning backtest artifacts into visual
representations. It should consume computed data such as equity curves and
trade logs, but it should not run backtests, define canonical metric formulas,
or persist files.
"""

from typing import TYPE_CHECKING, Any

import pandas as pd

from .schemas import EquityCurveFrame

REPORT_EQUITY_CURVE_REQUIRED_COLUMNS = (
    "datetime",
    "equity",
    "close",
)

if TYPE_CHECKING:
    import plotly.graph_objects as go


def build_equity_curve_figure(equity_curve: EquityCurveFrame) -> go.Figure:
    """Build an equity-curve figure from computed backtest results."""
    # Figure construction belongs here so backtest.py remains computation-only.
    _validate_equity_curve_columns(
        equity_curve,
        required_columns=REPORT_EQUITY_CURVE_REQUIRED_COLUMNS[:2],
    )
    go = _load_plotly_graph_objects()

    time_values = pd.to_datetime(equity_curve["datetime"])
    equity_values = equity_curve["equity"].astype(float)

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=time_values,
            y=equity_values,
            mode="lines",
            name="Strategy Equity",
            hovertemplate="Time=%{x}<br>Equity=%{y:,.2f}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Strategy Equity Curve",
        xaxis_title="Time",
        yaxis_title="Portfolio Value",
        template="plotly_white",
        hovermode="x unified",
    )
    return figure


def build_strategy_benchmark_figure(
    strategy_equity_curve: EquityCurveFrame,
    benchmark_equity_curve: EquityCurveFrame,
) -> go.Figure:
    """Build a comparison figure for strategy equity versus buy-and-hold."""
    _validate_equity_curve_columns(
        strategy_equity_curve,
        required_columns=REPORT_EQUITY_CURVE_REQUIRED_COLUMNS[:2],
    )
    _validate_equity_curve_columns(
        benchmark_equity_curve,
        required_columns=REPORT_EQUITY_CURVE_REQUIRED_COLUMNS[:2],
    )
    go = _load_plotly_graph_objects()

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=pd.to_datetime(strategy_equity_curve["datetime"]),
            y=strategy_equity_curve["equity"].astype(float),
            mode="lines",
            name="Strategy Equity",
            hovertemplate="Time=%{x}<br>Equity=%{y:,.2f}<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=pd.to_datetime(benchmark_equity_curve["datetime"]),
            y=benchmark_equity_curve["equity"].astype(float),
            mode="lines",
            name="Buy and Hold",
            hovertemplate="Time=%{x}<br>Equity=%{y:,.2f}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Strategy vs Buy-and-Hold",
        xaxis_title="Time",
        yaxis_title="Portfolio Value",
        template="plotly_white",
        hovermode="x unified",
    )
    return figure


def build_drawdown_figure(equity_curve: EquityCurveFrame) -> go.Figure:
    """Build a drawdown figure from the backtest equity curve."""
    # Drawdown presentation belongs here even if drawdown metrics are computed elsewhere.
    _validate_equity_curve_columns(
        equity_curve,
        required_columns=REPORT_EQUITY_CURVE_REQUIRED_COLUMNS[:2],
    )
    go = _load_plotly_graph_objects()

    time_values = pd.to_datetime(equity_curve["datetime"])
    drawdown_values = _compute_drawdown_series(equity_curve["equity"])

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=time_values,
            y=drawdown_values,
            mode="lines",
            name="Drawdown",
            fill="tozeroy",
            hovertemplate="Time=%{x}<br>Drawdown=%{y:.2%}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Strategy Drawdown",
        xaxis_title="Time",
        yaxis_title="Drawdown",
        template="plotly_white",
        hovermode="x unified",
    )
    return figure


def build_price_trade_figure(
    equity_curve: EquityCurveFrame,
    trades: pd.DataFrame,
) -> go.Figure:
    """Build a price-and-trade figure from the equity curve frame and trade log."""
    # Trade overlays belong here so storage.py does not become a plotting module.
    _validate_equity_curve_columns(
        equity_curve,
        required_columns=(REPORT_EQUITY_CURVE_REQUIRED_COLUMNS[0], REPORT_EQUITY_CURVE_REQUIRED_COLUMNS[2]),
    )
    go = _load_plotly_graph_objects()

    time_values = pd.to_datetime(equity_curve["datetime"])
    close_values = equity_curve["close"].astype(float)
    entry_markers = _build_trade_markers(trades, "entry_datetime", "entry_price")
    exit_markers = _build_trade_markers(trades, "exit_datetime", "exit_price")

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=time_values,
            y=close_values,
            mode="lines",
            name="Close Price",
            hovertemplate="Time=%{x}<br>Close=%{y:,.2f}<extra></extra>",
        )
    )
    if not entry_markers.empty:
        figure.add_trace(
            go.Scatter(
                x=entry_markers["time"],
                y=entry_markers["price"],
                mode="markers",
                name="Buy",
                marker={"symbol": "triangle-up", "size": 11},
                hovertemplate="Entry=%{x}<br>Price=%{y:,.2f}<extra></extra>",
            )
        )
    if not exit_markers.empty:
        figure.add_trace(
            go.Scatter(
                x=exit_markers["time"],
                y=exit_markers["price"],
                mode="markers",
                name="Sell",
                marker={"symbol": "triangle-down", "size": 11},
                hovertemplate="Exit=%{x}<br>Price=%{y:,.2f}<extra></extra>",
            )
        )
    figure.update_layout(
        title="Price with Trade Markers",
        xaxis_title="Time",
        yaxis_title="Close Price",
        template="plotly_white",
        hovermode="x unified",
    )
    return figure


def build_equity_comparison_figure(equity_curves: dict[str, EquityCurveFrame]) -> go.Figure:
    """Build an overlay figure comparing multiple ranked equity curves."""
    _validate_comparison_input(equity_curves)
    go = _load_plotly_graph_objects()

    figure = go.Figure()
    for label, equity_curve in equity_curves.items():
        _validate_equity_curve_columns(
            equity_curve,
            required_columns=REPORT_EQUITY_CURVE_REQUIRED_COLUMNS[:2],
        )
        figure.add_trace(
            go.Scatter(
                x=pd.to_datetime(equity_curve["datetime"]),
                y=equity_curve["equity"].astype(float),
                mode="lines",
                name=label,
                hovertemplate="Time=%{x}<br>Equity=%{y:,.2f}<extra>%{fullData.name}</extra>",
            )
        )
    figure.update_layout(
        title="Top Ranked Equity Curves",
        xaxis_title="Time",
        yaxis_title="Portfolio Value",
        template="plotly_white",
        hovermode="x unified",
    )
    return figure


def build_drawdown_comparison_figure(equity_curves: dict[str, EquityCurveFrame]) -> go.Figure:
    """Build an overlay figure comparing drawdown across ranked equity curves."""
    _validate_comparison_input(equity_curves)
    go = _load_plotly_graph_objects()

    figure = go.Figure()
    for label, equity_curve in equity_curves.items():
        _validate_equity_curve_columns(
            equity_curve,
            required_columns=REPORT_EQUITY_CURVE_REQUIRED_COLUMNS[:2],
        )
        figure.add_trace(
            go.Scatter(
                x=pd.to_datetime(equity_curve["datetime"]),
                y=_compute_drawdown_series(equity_curve["equity"]),
                mode="lines",
                name=label,
                hovertemplate="Time=%{x}<br>Drawdown=%{y:.2%}<extra>%{fullData.name}</extra>",
            )
        )
    figure.update_layout(
        title="Top Ranked Drawdowns",
        xaxis_title="Time",
        yaxis_title="Drawdown",
        template="plotly_white",
        hovermode="x unified",
    )
    return figure


def _validate_equity_curve_columns(
    equity_curve: EquityCurveFrame,
    required_columns: tuple[str, ...],
) -> None:
    missing_columns = [column for column in required_columns if column not in equity_curve.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Equity curve is missing required columns: {missing}")


def _compute_drawdown_series(equity: pd.Series) -> pd.Series:
    equity_values = equity.astype(float)
    running_peak = equity_values.cummax()
    return (equity_values / running_peak) - 1.0


def _validate_comparison_input(equity_curves: dict[str, EquityCurveFrame]) -> None:
    if not equity_curves:
        raise ValueError("At least one equity curve is required for comparison visualization")


def _build_trade_markers(trades: pd.DataFrame, time_column: str, price_column: str) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["time", "price"])

    required_columns = [time_column, price_column]
    missing_columns = [column for column in required_columns if column not in trades.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Trade log is missing required columns: {missing}")

    markers = trades.loc[:, required_columns].copy()
    markers.columns = ["time", "price"]
    markers["time"] = pd.to_datetime(markers["time"])
    markers["price"] = markers["price"].astype(float)
    return markers.dropna(subset=["time", "price"])


def _load_plotly_graph_objects():
    try:
        import plotly.graph_objects as go
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "plotly is required for AlphaForge visualizations. Install project dependencies or add plotly to the environment."
        ) from exc
    return go
