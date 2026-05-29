from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from alphaforge.dashboard_artifacts import (
    DashboardArtifactBundle,
    load_dashboard_artifacts,
    pipeline_step_statuses,
)


DEFAULT_ARTIFACT_DIR = "artifacts/phase25/ml_artifact_smoke"


def main() -> None:
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised manually
        raise SystemExit(
            "Streamlit is not installed. Install the dashboard extra with: "
            "python3 -m pip install -e '.[dashboard]'"
        ) from exc

    st.set_page_config(page_title="AlphaForge Research Dashboard", layout="wide")
    st.title("AlphaForge Research Dashboard")
    st.caption(
        "Local-first dashboard for ML research artifacts: labels, datasets, "
        "predictions, signals, metrics, and reports."
    )

    artifact_dir = st.sidebar.text_input("Artifact directory", DEFAULT_ARTIFACT_DIR)
    preview_rows = st.sidebar.slider("Preview rows", min_value=1, max_value=25, value=5)
    bundle = load_dashboard_artifacts(Path(artifact_dir), preview_rows=preview_rows)

    render_overview(st, bundle)
    render_pipeline(st, bundle)
    render_metrics(st, bundle)
    render_diagnostics(st, bundle)
    render_tables(st, bundle)
    render_report(st, bundle)


def render_overview(st: Any, bundle: DashboardArtifactBundle) -> None:
    st.subheader("Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Expected files", len(bundle.expected_files))
    col2.metric("Present files", len(bundle.present_files))
    col3.metric("Missing files", len(bundle.missing_files))
    col4.metric("Complete", "Yes" if bundle.is_complete else "No")

    if bundle.missing_files:
        st.warning("Missing artifacts: " + ", ".join(bundle.missing_files))
    else:
        st.success("All expected Phase 27 dashboard artifacts are present.")


def render_pipeline(st: Any, bundle: DashboardArtifactBundle) -> None:
    st.subheader("Pipeline Status")
    steps = pd.DataFrame(pipeline_step_statuses(bundle))
    st.dataframe(steps, use_container_width=True)

    row_counts = []
    labels = {
        "return_labels": "Return labels",
        "supervised_panel": "Supervised panel",
        "dataset": "Dataset",
        "predictions": "Predictions",
        "ml_signal": "ML signal",
    }
    for name, label in labels.items():
        summary = bundle.table_summaries.get(name)
        if summary is not None and summary.exists and summary.row_count is not None:
            row_counts.append({"stage": label, "rows": summary.row_count})
    if row_counts:
        st.caption("Rows carried through each ML artifact stage")
        st.bar_chart(pd.DataFrame(row_counts).set_index("stage"))


def render_metrics(st: Any, bundle: DashboardArtifactBundle) -> None:
    st.subheader("JSON Summaries")
    if not bundle.json_summaries:
        st.info("No JSON summaries found.")
        return

    for name, data in bundle.json_summaries.items():
        with st.expander(name, expanded=name == "metrics_summary"):
            st.json(data)


def render_diagnostics(st: Any, bundle: DashboardArtifactBundle) -> None:
    st.subheader("ML Artifact Diagnostics")
    predictions = read_table(bundle, "predictions")
    signal = read_table(bundle, "ml_signal")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Signal direction counts**")
        if signal is None or "direction" not in signal.columns:
            st.info("ml_signal.csv with direction column is required.")
        else:
            counts = (
                signal["direction"]
                .map({1: "long", 0: "neutral", -1: "short"})
                .fillna(signal["direction"].astype(str))
                .value_counts()
                .rename_axis("direction")
                .reset_index(name="count")
            )
            st.bar_chart(counts.set_index("direction"))

    with col2:
        st.markdown("**Target weight by asset**")
        required = {"asset_id", "target_weight"}
        if signal is None or not required.issubset(signal.columns):
            st.info("ml_signal.csv with asset_id and target_weight columns is required.")
        else:
            weight_frame = signal[["asset_id", "target_weight"]].copy()
            weight_frame["target_weight"] = pd.to_numeric(weight_frame["target_weight"], errors="coerce")
            st.bar_chart(weight_frame.set_index("asset_id"))

    st.markdown("**Predicted vs realized forward return**")
    if predictions is None:
        st.info("predictions.csv is required.")
        return

    if {"predicted_return", "ret_fwd_1m"}.issubset(predictions.columns):
        scatter = predictions[["predicted_return", "ret_fwd_1m"]].copy()
        scatter["predicted_return"] = pd.to_numeric(scatter["predicted_return"], errors="coerce")
        scatter["ret_fwd_1m"] = pd.to_numeric(scatter["ret_fwd_1m"], errors="coerce")
        st.scatter_chart(scatter, x="predicted_return", y="ret_fwd_1m")
    else:
        st.info("predictions.csv must include predicted_return and ret_fwd_1m columns.")


def render_tables(st: Any, bundle: DashboardArtifactBundle) -> None:
    st.subheader("Artifact Tables")
    tabs = st.tabs(list(bundle.table_summaries.keys()))
    for tab, (name, summary) in zip(tabs, bundle.table_summaries.items()):
        with tab:
            if not summary.exists:
                st.info(f"{name} not found at {summary.path}")
                continue
            if summary.error:
                st.error(f"Could not read {name}: {summary.error}")
                continue
            c1, c2 = st.columns(2)
            c1.metric("Rows", summary.row_count)
            c2.metric("Columns", summary.column_count)
            st.caption("Columns: " + ", ".join(summary.columns))
            if summary.preview_rows:
                st.dataframe(pd.DataFrame(summary.preview_rows), use_container_width=True)


def render_report(st: Any, bundle: DashboardArtifactBundle) -> None:
    st.subheader("HTML Report")
    if not bundle.report_exists or bundle.report_path is None:
        st.info("report.html not found.")
        return

    report_path = Path(bundle.report_path)
    st.caption(str(report_path))
    st.info(
        "This embedded report is a generic artifact report. For the ML smoke, "
        "backtest-only files such as equity_curve.csv and trade_log.csv are expected to be missing."
    )
    try:
        html = report_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        html = report_path.read_text(errors="ignore")
    st.components.v1.html(html, height=700, scrolling=True)


def read_table(bundle: DashboardArtifactBundle, name: str) -> pd.DataFrame | None:
    summary = bundle.table_summaries.get(name)
    if summary is None or not summary.exists or summary.error:
        return None
    try:
        return pd.read_csv(summary.path)
    except Exception:  # pragma: no cover - defensive for corrupted local artifacts
        return None


if __name__ == "__main__":
    main()
