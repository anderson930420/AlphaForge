from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px

from alphaforge.dashboard_artifacts import (
    FactorDiagnosticsBundle,
    factor_diagnostic_step_statuses,
)


def render_factor_diagnostics_dashboard(st: Any, bundle: FactorDiagnosticsBundle) -> None:
    st.subheader("Factor Diagnostics")
    if not bundle.has_any_artifacts:
        st.info(
            "No factor diagnostics artifacts found. Generate them with "
            "scripts/run_factor_diagnostics.py, then set the directory in the sidebar."
        )
        return

    status = pd.DataFrame(factor_diagnostic_step_statuses(bundle))
    st.dataframe(status, use_container_width=True, hide_index=True)
    if bundle.missing_files:
        st.warning("Missing factor diagnostic artifacts: " + ", ".join(bundle.missing_files))

    render_factor_summary(st, bundle.summary)

    coverage = read_factor_table(bundle, "coverage_by_date")
    ic = read_factor_table(bundle, "ic_timeseries")
    quantile_returns = read_factor_table(bundle, "quantile_returns")
    spread = read_factor_table(bundle, "long_short_spread")

    col1, col2 = st.columns(2)
    with col1:
        render_coverage(st, coverage)
    with col2:
        render_ic(st, ic)

    render_quantile_returns(st, quantile_returns)
    render_long_short_spread(st, spread)


def render_factor_summary(st: Any, summary: dict[str, Any] | None) -> None:
    if summary is None:
        st.info("factor_summary.json not found.")
        return

    st.markdown("**Factor summary**")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Factor", str(summary.get("factor_col", "N/A")))
    col2.metric("Rows", _format_int(summary.get("row_count")))
    col3.metric("Dates", _format_int(summary.get("date_count")))
    col4.metric("Assets", _format_int(summary.get("asset_count")))

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Coverage", _format_percent(summary.get("mean_coverage_ratio")))
    col6.metric("IC mean", _format_decimal(summary.get("ic_mean")))
    col7.metric("Rank IC mean", _format_decimal(summary.get("rank_ic_mean")))
    col8.metric("Long-short mean", _format_decimal(summary.get("long_short_spread_mean")))

    with st.expander("Raw factor_summary.json"):
        st.json(summary)


def render_coverage(st: Any, frame: pd.DataFrame | None) -> None:
    st.markdown("**Coverage by date**")
    if frame is None or frame.empty:
        st.info("factor_coverage_by_date.csv has no rows.")
        return
    if not {"date", "coverage_ratio"}.issubset(frame.columns):
        st.info("Coverage table must include date and coverage_ratio columns.")
        return

    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["coverage_ratio"] = pd.to_numeric(data["coverage_ratio"], errors="coerce")
    data = data.dropna(subset=["date", "coverage_ratio"])
    if data.empty:
        st.info("Coverage table has no valid numeric rows.")
        return

    fig = px.line(data, x="date", y="coverage_ratio", markers=True)
    fig.update_layout(xaxis_title="Date", yaxis_title="Coverage ratio", height=330)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(data, use_container_width=True, hide_index=True)


def render_ic(st: Any, frame: pd.DataFrame | None) -> None:
    st.markdown("**IC / Rank IC by date**")
    if frame is None or frame.empty:
        st.info("factor_ic_timeseries.csv has no rows.")
        return
    if not {"date", "ic", "rank_ic"}.issubset(frame.columns):
        st.info("IC table must include date, ic, and rank_ic columns.")
        return

    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["ic"] = pd.to_numeric(data["ic"], errors="coerce")
    data["rank_ic"] = pd.to_numeric(data["rank_ic"], errors="coerce")
    data = data.dropna(subset=["date"])
    if data[["ic", "rank_ic"]].dropna(how="all").empty:
        st.info("IC table has dates but no valid IC values.")
        st.dataframe(data, use_container_width=True, hide_index=True)
        return

    long = data.melt(id_vars="date", value_vars=["ic", "rank_ic"], var_name="metric", value_name="value")
    fig = px.line(long, x="date", y="value", color="metric", markers=True)
    fig.update_layout(xaxis_title="Date", yaxis_title="Correlation", height=330)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(data, use_container_width=True, hide_index=True)


def render_quantile_returns(st: Any, frame: pd.DataFrame | None) -> None:
    st.markdown("**Quantile forward returns**")
    if frame is None or frame.empty:
        st.info(
            "factor_quantile_returns.csv has no rows. This is expected when the requested "
            "quantile count is larger than the available per-date cross section."
        )
        return
    if not {"date", "quantile", "mean_forward_return"}.issubset(frame.columns):
        st.info("Quantile return table must include date, quantile, and mean_forward_return columns.")
        return

    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["mean_forward_return"] = pd.to_numeric(data["mean_forward_return"], errors="coerce")
    data = data.dropna(subset=["date", "mean_forward_return"])
    if data.empty:
        st.info("Quantile return table has no valid numeric rows.")
        return

    fig = px.bar(data, x="date", y="mean_forward_return", color="quantile", barmode="group")
    fig.update_layout(xaxis_title="Date", yaxis_title="Mean forward return", height=420)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(data, use_container_width=True, hide_index=True)


def render_long_short_spread(st: Any, frame: pd.DataFrame | None) -> None:
    st.markdown("**Long-short spread**")
    if frame is None or frame.empty:
        st.info(
            "factor_long_short_spread.csv has no rows. This is expected for thin fixtures "
            "or when quantile buckets could not be formed."
        )
        return
    if not {"date", "long_short_spread"}.issubset(frame.columns):
        st.info("Long-short spread table must include date and long_short_spread columns.")
        return

    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["long_short_spread"] = pd.to_numeric(data["long_short_spread"], errors="coerce")
    data = data.dropna(subset=["date", "long_short_spread"])
    if data.empty:
        st.info("Long-short spread table has no valid numeric rows.")
        return

    fig = px.line(data, x="date", y="long_short_spread", markers=True)
    fig.update_layout(xaxis_title="Date", yaxis_title="Top minus bottom forward return", height=380)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(data, use_container_width=True, hide_index=True)


def read_factor_table(bundle: FactorDiagnosticsBundle, name: str) -> pd.DataFrame | None:
    summary = bundle.table_summaries.get(name)
    if summary is None or not summary.exists or summary.error:
        return None
    try:
        return pd.read_csv(summary.path)
    except Exception:  # pragma: no cover - defensive for corrupted local artifacts
        return None


def _format_int(value: Any) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    try:
        return f"{int(value)}"
    except (TypeError, ValueError):
        return str(value)


def _format_decimal(value: Any) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _format_percent(value: Any) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(value)
