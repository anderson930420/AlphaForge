from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px

from alphaforge.dashboard_artifacts import (
    DashboardArtifactBundle,
    load_dashboard_artifacts,
    load_factor_diagnostics_artifacts,
    pipeline_step_statuses,
)
from alphaforge.dashboard_factor import render_factor_diagnostics_dashboard


DEFAULT_ARTIFACT_DIR = "artifacts/phase25/ml_artifact_smoke"
DEFAULT_FACTOR_DIAGNOSTICS_DIR = "artifacts/phase28/mom12m_diagnostics_q2"
PIPELINE_ROW_ORDER = [
    "Return labels",
    "Supervised panel",
    "Dataset",
    "Predictions",
    "ML signal",
]
DIRECTION_ORDER = ["long", "neutral", "short"]


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
        "predictions, signals, factor diagnostics, metrics, and reports."
    )

    artifact_dir = st.sidebar.text_input("ML artifact directory", DEFAULT_ARTIFACT_DIR)
    factor_dir = st.sidebar.text_input("Factor diagnostics directory", DEFAULT_FACTOR_DIAGNOSTICS_DIR)
    preview_rows = st.sidebar.slider("Preview rows", min_value=1, max_value=25, value=5)

    bundle = load_dashboard_artifacts(Path(artifact_dir), preview_rows=preview_rows)
    factor_bundle = load_factor_diagnostics_artifacts(Path(factor_dir), preview_rows=preview_rows)

    render_overview(st, bundle)
    render_pipeline(st, bundle)
    render_metrics(st, bundle)
    render_factor_diagnostics_dashboard(st, factor_bundle)
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
    st.dataframe(steps, use_container_width=True, hide_index=True)

    row_counts = build_pipeline_row_counts(bundle)
    if not row_counts.empty:
        st.caption("Rows carried through each ML artifact stage")
        fig = px.bar(
            row_counts,
            x="rows",
            y="stage",
            orientation="h",
            text="rows",
            category_orders={"stage": PIPELINE_ROW_ORDER},
        )
        fig.update_layout(
            xaxis_title="Rows",
            yaxis_title="Stage",
            height=330,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(fig, use_container_width=True)


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

    if predictions is not None and len(predictions) < 10:
        st.info(
            "The current smoke fixture is intentionally tiny. Charts verify the dashboard wiring, "
            "but they are not meaningful research diagnostics yet. Use a larger artifact directory "
            "for realistic long/short and prediction-quality visuals."
        )

    col1, col2 = st.columns(2)
    with col1:
        render_direction_counts(st, signal)
    with col2:
        render_target_weights(st, signal)

    render_prediction_scatter(st, predictions)


def render_direction_counts(st: Any, signal: pd.DataFrame | None) -> None:
    st.markdown("**Signal direction mix**")
    if signal is None or "direction" not in signal.columns:
        st.info("ml_signal.csv with direction column is required.")
        return

    direction = pd.to_numeric(signal["direction"], errors="coerce")
    direction_labels = direction.map({1: "long", 0: "neutral", -1: "short"}).fillna("unknown")
    counts = (
        direction_labels.value_counts()
        .reindex(DIRECTION_ORDER + ["unknown"], fill_value=0)
        .rename_axis("direction")
        .reset_index(name="count")
    )
    counts = counts[counts["count"] > 0]
    total = int(counts["count"].sum())

    fig = px.pie(
        counts,
        names="direction",
        values="count",
        hole=0.55,
        category_orders={"direction": DIRECTION_ORDER + ["unknown"]},
    )
    fig.update_traces(textinfo="label+percent+value")
    fig.update_layout(
        height=330,
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        annotations=[
            {"text": f"{total}<br>signals", "x": 0.5, "y": 0.5, "font_size": 16, "showarrow": False}
        ],
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(counts, use_container_width=True, hide_index=True)

    if set(counts["direction"]) == {"neutral"}:
        st.caption(
            "All rows are neutral. This is expected for very small or low-dispersion smoke fixtures."
        )


def render_target_weights(st: Any, signal: pd.DataFrame | None) -> None:
    st.markdown("**Target weight by asset**")
    required = {"asset_id", "target_weight"}
    if signal is None or not required.issubset(signal.columns):
        st.info("ml_signal.csv with asset_id and target_weight columns is required.")
        return

    weight_frame = signal[["asset_id", "target_weight"]].copy()
    weight_frame["asset_id"] = weight_frame["asset_id"].astype(str)
    weight_frame["target_weight"] = pd.to_numeric(weight_frame["target_weight"], errors="coerce").fillna(0.0)

    fig = px.bar(weight_frame, x="asset_id", y="target_weight", text="target_weight")
    fig.update_layout(
        xaxis_title="Asset",
        yaxis_title="Target weight",
        height=330,
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
    )
    fig.update_traces(texttemplate="%{text:.3f}", textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(weight_frame, use_container_width=True, hide_index=True)

    if weight_frame["target_weight"].abs().sum() == 0:
        st.caption(
            "All target weights are zero because the generated signal is neutral for this tiny fixture."
        )


def render_prediction_scatter(st: Any, predictions: pd.DataFrame | None) -> None:
    st.markdown("**Predicted vs realized forward return**")
    if predictions is None:
        st.info("predictions.csv is required.")
        return

    if not {"predicted_return", "ret_fwd_1m"}.issubset(predictions.columns):
        st.info("predictions.csv must include predicted_return and ret_fwd_1m columns.")
        return

    scatter = predictions.copy()
    scatter["predicted_return"] = pd.to_numeric(scatter["predicted_return"], errors="coerce")
    scatter["ret_fwd_1m"] = pd.to_numeric(scatter["ret_fwd_1m"], errors="coerce")
    scatter = scatter.dropna(subset=["predicted_return", "ret_fwd_1m"])

    hover_cols = [col for col in ["asset_id", "date"] if col in scatter.columns]
    fig = px.scatter(scatter, x="predicted_return", y="ret_fwd_1m", hover_data=hover_cols)
    fig.update_layout(
        xaxis_title="Predicted return",
        yaxis_title="Realized forward return",
        height=430,
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(scatter, use_container_width=True, hide_index=True)


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


def build_pipeline_row_counts(bundle: DashboardArtifactBundle) -> pd.DataFrame:
    labels = {
        "return_labels": "Return labels",
        "supervised_panel": "Supervised panel",
        "dataset": "Dataset",
        "predictions": "Predictions",
        "ml_signal": "ML signal",
    }
    rows = []
    for name, label in labels.items():
        summary = bundle.table_summaries.get(name)
        if summary is not None and summary.exists and summary.row_count is not None:
            rows.append({"stage": label, "rows": summary.row_count})
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["stage"] = pd.Categorical(frame["stage"], categories=PIPELINE_ROW_ORDER, ordered=True)
    return frame.sort_values("stage")


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
