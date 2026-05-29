from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px

from alphaforge.dashboard_artifacts import TableSummary, load_json_artifact, summarize_csv_artifact


ML_PREDICTION_DIAGNOSTIC_ARTIFACTS: tuple[str, ...] = (
    "ml_prediction_summary.json",
    "ml_prediction_ic_timeseries.csv",
    "ml_prediction_quantile_returns.csv",
    "ml_prediction_long_short_spread.csv",
    "ml_prediction_error_by_date.csv",
)

ML_PREDICTION_TABLE_ARTIFACTS = {
    "ic_timeseries": "ml_prediction_ic_timeseries.csv",
    "quantile_returns": "ml_prediction_quantile_returns.csv",
    "long_short_spread": "ml_prediction_long_short_spread.csv",
    "error_by_date": "ml_prediction_error_by_date.csv",
}


@dataclass(frozen=True)
class MLPredictionDiagnosticsBundle:
    diagnostics_dir: str
    expected_files: tuple[str, ...]
    present_files: tuple[str, ...]
    missing_files: tuple[str, ...]
    summary: dict[str, Any] | None
    table_summaries: dict[str, TableSummary]

    @property
    def is_complete(self) -> bool:
        return not self.missing_files

    @property
    def has_any_artifacts(self) -> bool:
        return bool(self.present_files)


def load_ml_prediction_diagnostics_artifacts(
    diagnostics_dir: Path | str,
    *,
    preview_rows: int = 5,
) -> MLPredictionDiagnosticsBundle:
    root = Path(diagnostics_dir).expanduser()
    present_files = []
    missing_files = []
    for filename in ML_PREDICTION_DIAGNOSTIC_ARTIFACTS:
        path = root / filename
        if path.exists():
            present_files.append(filename)
        else:
            missing_files.append(filename)

    summary_path = root / "ml_prediction_summary.json"
    summary = load_json_artifact(summary_path) if summary_path.exists() else None
    table_summaries = {
        name: summarize_csv_artifact(root / filename, name=name, preview_rows=preview_rows)
        for name, filename in ML_PREDICTION_TABLE_ARTIFACTS.items()
    }

    return MLPredictionDiagnosticsBundle(
        diagnostics_dir=str(root),
        expected_files=ML_PREDICTION_DIAGNOSTIC_ARTIFACTS,
        present_files=tuple(present_files),
        missing_files=tuple(missing_files),
        summary=summary,
        table_summaries=table_summaries,
    )


def ml_prediction_diagnostic_step_statuses(bundle: MLPredictionDiagnosticsBundle) -> list[dict[str, Any]]:
    labels = {
        "ml_prediction_summary.json": "Summary statistics",
        "ml_prediction_ic_timeseries.csv": "Prediction IC / Rank IC",
        "ml_prediction_quantile_returns.csv": "Prediction quantile returns",
        "ml_prediction_long_short_spread.csv": "Prediction long-short spread",
        "ml_prediction_error_by_date.csv": "Prediction error by date",
    }
    present = set(bundle.present_files)
    return [
        {
            "artifact": filename,
            "stage": labels[filename],
            "status": "present" if filename in present else "missing",
        }
        for filename in ML_PREDICTION_DIAGNOSTIC_ARTIFACTS
    ]


def render_ml_prediction_diagnostics_dashboard(st: Any, bundle: MLPredictionDiagnosticsBundle) -> None:
    st.subheader("ML Prediction Diagnostics")
    if not bundle.has_any_artifacts:
        st.info(
            "No ML prediction diagnostics artifacts found. Generate them with "
            "scripts/run_ml_prediction_diagnostics.py or scripts/run_synthetic_prediction_demo.py, "
            "then set the directory in the sidebar."
        )
        return

    status = pd.DataFrame(ml_prediction_diagnostic_step_statuses(bundle))
    st.dataframe(status, use_container_width=True, hide_index=True)
    if bundle.missing_files:
        st.warning("Missing ML prediction diagnostic artifacts: " + ", ".join(bundle.missing_files))

    render_prediction_summary(st, bundle.summary)
    ic = read_prediction_table(bundle, "ic_timeseries")
    quantile_returns = read_prediction_table(bundle, "quantile_returns")
    spread = read_prediction_table(bundle, "long_short_spread")
    errors = read_prediction_table(bundle, "error_by_date")

    render_prediction_ic(st, ic)
    render_prediction_quantile_returns(st, quantile_returns)
    render_prediction_long_short_spread(st, spread)
    render_prediction_errors(st, errors)


def render_prediction_summary(st: Any, summary: dict[str, Any] | None) -> None:
    if summary is None:
        st.info("ml_prediction_summary.json not found.")
        return

    st.markdown("**Prediction summary**")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", _format_int(summary.get("row_count")))
    col2.metric("Dates", _format_int(summary.get("date_count")))
    col3.metric("Assets", _format_int(summary.get("asset_count")))
    col4.metric("Quantiles", _format_int(summary.get("quantiles")))

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("IC mean", _format_decimal(summary.get("prediction_ic_mean")))
    col6.metric("Rank IC mean", _format_decimal(summary.get("prediction_rank_ic_mean")))
    col7.metric("Long-short mean", _format_decimal(summary.get("long_short_spread_mean")))
    col8.metric("MAE", _format_decimal(summary.get("overall_mae")))

    with st.expander("Raw ml_prediction_summary.json"):
        st.json(summary)


def render_prediction_ic(st: Any, frame: pd.DataFrame | None) -> None:
    st.markdown("**Prediction IC / Rank IC by date**")
    if frame is None or frame.empty:
        st.info("ml_prediction_ic_timeseries.csv has no rows.")
        return
    if not {"date", "prediction_ic", "prediction_rank_ic"}.issubset(frame.columns):
        st.info("IC table must include date, prediction_ic, and prediction_rank_ic columns.")
        return

    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["prediction_ic"] = pd.to_numeric(data["prediction_ic"], errors="coerce")
    data["prediction_rank_ic"] = pd.to_numeric(data["prediction_rank_ic"], errors="coerce")
    data = data.dropna(subset=["date"])
    if data[["prediction_ic", "prediction_rank_ic"]].dropna(how="all").empty:
        st.info("IC table has dates but no valid IC values.")
        st.dataframe(data, use_container_width=True, hide_index=True)
        return

    long = data.melt(
        id_vars="date",
        value_vars=["prediction_ic", "prediction_rank_ic"],
        var_name="metric",
        value_name="value",
    )
    fig = px.line(long, x="date", y="value", color="metric", markers=True)
    fig.update_layout(xaxis_title="Date", yaxis_title="Correlation", height=360)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(data, use_container_width=True, hide_index=True)


def render_prediction_quantile_returns(st: Any, frame: pd.DataFrame | None) -> None:
    st.markdown("**Prediction quantile forward returns**")
    if frame is None or frame.empty:
        st.info(
            "ml_prediction_quantile_returns.csv has no rows. This is expected when the requested "
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
    fig.update_layout(xaxis_title="Date", yaxis_title="Mean realized forward return", height=430)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(data, use_container_width=True, hide_index=True)


def render_prediction_long_short_spread(st: Any, frame: pd.DataFrame | None) -> None:
    st.markdown("**Prediction long-short spread**")
    if frame is None or frame.empty:
        st.info(
            "ml_prediction_long_short_spread.csv has no rows. This is expected for thin fixtures "
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
    fig.update_layout(xaxis_title="Date", yaxis_title="Top minus bottom realized forward return", height=380)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(data, use_container_width=True, hide_index=True)


def render_prediction_errors(st: Any, frame: pd.DataFrame | None) -> None:
    st.markdown("**Prediction error by date**")
    if frame is None or frame.empty:
        st.info("ml_prediction_error_by_date.csv has no rows.")
        return
    if not {"date", "mse", "mae", "mean_error"}.issubset(frame.columns):
        st.info("Error table must include date, mse, mae, and mean_error columns.")
        return

    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    for column in ["mse", "mae", "mean_error", "mean_prediction", "mean_label"]:
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["date"])
    if data[["mse", "mae", "mean_error"]].dropna(how="all").empty:
        st.info("Error table has dates but no valid error values.")
        st.dataframe(data, use_container_width=True, hide_index=True)
        return

    long = data.melt(id_vars="date", value_vars=["mse", "mae", "mean_error"], var_name="metric", value_name="value")
    fig = px.line(long, x="date", y="value", color="metric", markers=True)
    fig.update_layout(xaxis_title="Date", yaxis_title="Error metric", height=380)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(data, use_container_width=True, hide_index=True)


def read_prediction_table(bundle: MLPredictionDiagnosticsBundle, name: str) -> pd.DataFrame | None:
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
