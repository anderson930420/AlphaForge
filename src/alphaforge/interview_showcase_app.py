from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px

from alphaforge.interview_showcase import (
    DEFAULT_INTERVIEW_RUN_DIR,
    DEFAULT_SHOWCASE_ROOT,
    build_artifact_trace,
    build_health_checks,
    discover_artifact_run_dirs,
    extract_artifact_zip,
    extract_overview_metrics,
    load_interview_showcase_artifacts,
    summarize_signal_exposure,
)


UPLOAD_ROOT = Path("artifacts/uploaded_showcase_runs")


def main() -> None:
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised manually
        raise SystemExit(
            "Streamlit is not installed. Install the dashboard extra with: "
            "python3 -m pip install -e '.[dashboard]'"
        ) from exc

    st.set_page_config(page_title="AlphaForge Interview Showcase", layout="wide")
    st.title("AlphaForge Interview Showcase")
    st.caption(
        "Read-only showcase for already-generated ML research artifacts. "
        "Use it locally or deploy it as a Streamlit app with bundled/uploaded artifact runs."
    )

    run_dir = select_run_dir(st)
    preview_rows = st.sidebar.slider("Preview rows", min_value=3, max_value=50, value=10)
    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Generate a default run with: `bash scripts/run_interview_demo.sh artifacts/demo/interview_ml_demo_C`."
    )

    artifacts = load_interview_showcase_artifacts(run_dir)
    st.caption(f"Current artifact run: `{run_dir}`")

    tabs = st.tabs([
        "Overview",
        "Health Checks",
        "Signal / Exposure",
        "Predictions",
        "Final Holdout",
        "HTML Showcase",
        "Artifact Trace",
        "Boundaries",
    ])
    with tabs[0]:
        render_overview(st, artifacts)
    with tabs[1]:
        render_health_checks(st, artifacts)
    with tabs[2]:
        render_signal(st, artifacts, preview_rows)
    with tabs[3]:
        render_predictions(st, artifacts, preview_rows)
    with tabs[4]:
        render_final_holdout(st, artifacts, preview_rows)
    with tabs[5]:
        render_html_showcase(st, artifacts)
    with tabs[6]:
        render_artifact_trace(st, run_dir)
    with tabs[7]:
        render_boundaries(st)


def select_run_dir(st: Any) -> Path:
    st.sidebar.subheader("Artifact Source")
    source_mode = st.sidebar.radio(
        "Source mode",
        ["Local artifact run", "Upload artifact ZIP"],
        horizontal=False,
    )

    if source_mode == "Upload artifact ZIP":
        uploaded = st.sidebar.file_uploader("Upload artifact run ZIP", type=["zip"])
        if uploaded is not None:
            try:
                extracted = extract_artifact_zip(
                    uploaded.getvalue(),
                    target_root=UPLOAD_ROOT,
                    run_name=uploaded.name,
                )
            except Exception as exc:  # pragma: no cover - UI defensive path
                st.sidebar.error(f"Could not extract uploaded ZIP: {exc}")
            else:
                st.sidebar.success(f"Loaded uploaded run: {extracted}")
                return extracted
        st.sidebar.info("Upload a ZIP, or switch to Local artifact run.")

    discovered = discover_artifact_run_dirs(DEFAULT_SHOWCASE_ROOT)
    options = [str(path) for path in discovered]
    default = str(Path(DEFAULT_INTERVIEW_RUN_DIR))
    if default not in options:
        options.insert(0, default)
    options.append("Custom path")

    selected = st.sidebar.selectbox("Select local run", options, index=0)
    if selected == "Custom path":
        return Path(st.sidebar.text_input("Artifact run directory", default))
    return Path(selected)


def render_overview(st: Any, artifacts: Any) -> None:
    st.subheader("Run Overview")
    overview = extract_overview_metrics(artifacts)
    cols = st.columns(5)
    cols[0].metric("Model", _format_value(overview.get("model")))
    cols[1].metric("Predictions", _format_value(overview.get("predictions_rows")))
    cols[2].metric("ML Signal Rows", _format_value(overview.get("ml_signal_rows")))
    cols[3].metric("Validation", "Yes" if overview.get("does_run_research_validation") else "No")
    cols[4].metric("Symbol", _format_value(overview.get("symbol")))

    metric_cols = st.columns(5)
    metric_cols[0].metric("Selected Signal Rows", _format_value(overview.get("selected_signal_row_count")))
    metric_cols[1].metric("Nonzero Exposure", _format_value(overview.get("nonzero_target_weight_count")))
    metric_cols[2].metric("Total Return", _format_percent(overview.get("total_return")))
    metric_cols[3].metric("Max Drawdown", _format_percent(overview.get("max_drawdown")))
    metric_cols[4].metric("Trade Count", _format_value(overview.get("trade_count")))

    st.info(
        "Interpret fixture or small-sample performance metrics as integration evidence, "
        "not as proof of profitable alpha."
    )


def render_health_checks(st: Any, artifacts: Any) -> None:
    st.subheader("Demo Health Checks")
    checks = pd.DataFrame(build_health_checks(artifacts.research_summary))
    if checks.empty:
        st.warning("No health checks available.")
        return
    pass_count = int((checks["status"] == "pass").sum())
    fail_count = int((checks["status"] == "fail").sum())
    warn_count = int((checks["status"] == "warn").sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Passed", pass_count)
    c2.metric("Warnings", warn_count)
    c3.metric("Failed", fail_count)
    if fail_count:
        st.error("One or more demo health checks failed. Do not use this run for interview presentation.")
    elif warn_count:
        st.warning("Demo completed with warnings. Review before presenting.")
    else:
        st.success("Health checks passed: nonzero exposure, date alignment, non-flat symbol, and no warnings.")
    st.dataframe(checks, use_container_width=True, hide_index=True)


def render_signal(st: Any, artifacts: Any, preview_rows: int) -> None:
    st.subheader("ML Signal and Exposure")
    exposure = summarize_signal_exposure(artifacts.signal)
    if exposure.empty:
        st.info("No signal exposure summary available.")
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            fig = px.bar(
                exposure,
                x="symbol",
                y="total_abs_weight",
                text="nonzero_target_weight_count",
                hover_data=["rows"],
            )
            fig.update_layout(
                height=320,
                margin={"l": 20, "r": 20, "t": 20, "b": 20},
                yaxis_title="Total absolute target weight",
            )
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(
                exposure,
                names="symbol",
                values="total_abs_weight",
                hole=0.55,
            )
            fig.update_layout(height=320, margin={"l": 20, "r": 20, "t": 20, "b": 20})
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(exposure, use_container_width=True, hide_index=True)

    if artifacts.signal is not None:
        st.markdown("**Cross-sectional ML signal**")
        st.dataframe(artifacts.signal.head(preview_rows), use_container_width=True, hide_index=True)
    if artifacts.derived_signal is not None:
        st.markdown("**Projected single-symbol validation signal**")
        st.dataframe(artifacts.derived_signal.head(preview_rows), use_container_width=True, hide_index=True)


def render_predictions(st: Any, artifacts: Any, preview_rows: int) -> None:
    st.subheader("Predictions")
    predictions = artifacts.predictions
    if predictions is None or predictions.empty:
        st.info("No model predictions found.")
        return
    if {"predicted_return", "ret_fwd_1m"}.issubset(predictions.columns):
        fig = px.scatter(
            predictions,
            x="predicted_return",
            y="ret_fwd_1m",
            hover_data=[col for col in ["asset_id", "date"] if col in predictions.columns],
        )
        fig.update_layout(
            height=380,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            xaxis_title="Predicted return",
            yaxis_title="Realized forward return",
        )
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(predictions.head(preview_rows), use_container_width=True, hide_index=True)


def render_final_holdout(st: Any, artifacts: Any, preview_rows: int) -> None:
    st.subheader("Final Holdout")
    metrics = artifacts.final_holdout_metrics or {}
    if metrics:
        cols = st.columns(6)
        cols[0].metric("Total Return", _format_percent(metrics.get("total_return")))
        cols[1].metric("Sharpe", _format_number(metrics.get("sharpe_ratio")))
        cols[2].metric("Max Drawdown", _format_percent(metrics.get("max_drawdown")))
        cols[3].metric("Turnover", _format_number(metrics.get("turnover")))
        cols[4].metric("Trades", _format_value(metrics.get("trade_count")))
        cols[5].metric("Bars", _format_value(metrics.get("bar_count")))
    else:
        st.info("No final-holdout metrics found.")

    equity = artifacts.equity_curve
    if equity is not None and not equity.empty and {"datetime", "equity"}.issubset(equity.columns):
        eq = equity.copy()
        eq["datetime"] = pd.to_datetime(eq["datetime"], errors="coerce")
        eq["equity"] = pd.to_numeric(eq["equity"], errors="coerce")
        eq = eq.dropna(subset=["datetime", "equity"])
        col1, col2 = st.columns(2)
        with col1:
            fig = px.line(eq, x="datetime", y="equity", markers=True)
            fig.update_layout(height=380, margin={"l": 20, "r": 20, "t": 20, "b": 20})
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            drawdown = eq.copy()
            drawdown["cummax"] = drawdown["equity"].cummax()
            drawdown["drawdown"] = drawdown["equity"] / drawdown["cummax"] - 1.0
            fig = px.area(drawdown, x="datetime", y="drawdown")
            fig.update_layout(height=380, margin={"l": 20, "r": 20, "t": 20, "b": 20})
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No final-holdout equity curve found.")

    trade_log = artifacts.trade_log
    if trade_log is not None and not trade_log.empty:
        st.markdown("**Trade log**")
        st.dataframe(trade_log.head(preview_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No final-holdout trade log found.")


def render_html_showcase(st: Any, artifacts: Any) -> None:
    st.subheader("Embedded HTML Showcase")
    report_path = Path(artifacts.html_report_path)
    if not report_path.exists():
        st.info(
            "No HTML report found. Generate one with `bash scripts/run_interview_demo.sh` "
            "or include `interview_artifact_report.html` in the artifact run."
        )
        return
    st.caption(str(report_path))
    try:
        html = report_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        html = report_path.read_text(errors="ignore")
    st.components.v1.html(html, height=850, scrolling=True)


def render_artifact_trace(st: Any, run_dir: Path) -> None:
    st.subheader("Artifact Trace")
    trace = build_artifact_trace(run_dir)
    st.dataframe(trace, use_container_width=True, hide_index=True)


def render_boundaries(st: Any) -> None:
    st.subheader("Boundaries")
    st.markdown(
        """
- This is a research artifact viewer, not a live trading system.
- It does not train models, run backtests, download data, or place orders.
- Fixture metrics are integration evidence, not alpha claims.
- Current `custom_signal` validation is single-symbol; multi-symbol portfolio validation is future work.
- SignalForge integration is file-based; AlphaForge does not import SignalForge runtime code.
"""
    )


def _format_value(value: Any) -> str:
    return "—" if value is None else str(value)


def _format_number(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return "—"


def _format_percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "—"


if __name__ == "__main__":
    main()
