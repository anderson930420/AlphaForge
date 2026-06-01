"""CRSP ML result diagnostics and benchmark comparison helpers.

This module reads existing CRSP ML E2E and Mom12m artifacts and turns them
into a research-oriented diagnostics artifact. It does not rerun training,
change dataset construction, change walk-forward splitting, or add new model
types.
"""

from __future__ import annotations

from datetime import datetime, timezone
from math import sqrt
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .dashboard_artifacts import load_json_artifact
from .json_utils import json_safe_float, write_json_artifact
from .parquet_io import read_parquet_artifact


REPORT_TITLE = "CRSP ML Result Diagnostics"

_ML_REQUIRED_JSON_FILENAMES = {
    "ml_e2e_summary": Path("e2e_summary.json"),
    "ml_sklearn_summary": Path("sklearn_baseline") / "summary.json",
    "ml_window_metrics": Path("sklearn_baseline") / "window_metrics.json",
}
_ML_REQUIRED_PARQUET_FILENAME = Path("sklearn_baseline") / "prediction_portfolio_returns.parquet"
_MOM12M_REQUIRED_JSON_FILENAMES = {
    "mom12m_summary": Path("momentum_summary.json"),
}
_MOM12M_REQUIRED_PARQUET_FILENAME = Path("momentum_portfolio_returns.parquet")
_WINDOW_METRIC_COLUMNS = ("mse", "mae", "prediction_ic", "prediction_rank_ic")
_WINDOW_EXTREMA_COLUMNS = ("prediction_ic", "prediction_rank_ic")
_PORTFOLIO_SUMMARY_KEYS = [
    "rows",
    "date_min",
    "date_max",
    "cumulative_return",
    "annualized_return",
    "annualized_volatility",
    "sharpe",
    "mean_monthly_return",
    "std_monthly_return",
    "positive_month_ratio",
    "best_month",
    "worst_month",
    "max_drawdown",
]


def load_crsp_ml_result_artifacts(
    *,
    ml_e2e_dir: str | Path,
    mom12m_dir: str | Path | None = None,
) -> dict[str, object]:
    """Load the existing CRSP ML and optional Mom12m artifacts.

    The returned bundle contains only already-generated artifacts. No pipeline
    work is performed here.
    """

    ml_root = Path(ml_e2e_dir).expanduser()
    if not ml_root.exists():
        raise FileNotFoundError(f"CRSP ML E2E artifact directory does not exist: {ml_root}")

    ml_required_paths = {
        key: ml_root / relative_path for key, relative_path in _ML_REQUIRED_JSON_FILENAMES.items()
    }
    ml_portfolio_returns_path = ml_root / _ML_REQUIRED_PARQUET_FILENAME

    ml_e2e_summary = _load_required_json_artifact(ml_required_paths["ml_e2e_summary"])
    ml_sklearn_summary = _load_required_json_artifact(ml_required_paths["ml_sklearn_summary"])
    ml_window_metrics_artifact = _load_required_json_artifact(ml_required_paths["ml_window_metrics"])
    ml_window_metrics = _require_window_metrics_list(ml_window_metrics_artifact, ml_required_paths["ml_window_metrics"])
    ml_portfolio_returns = _load_required_parquet_artifact(ml_portfolio_returns_path)

    artifact_paths: dict[str, str] = {
        "ml_e2e_dir": str(ml_root),
        "ml_e2e_summary": str(ml_required_paths["ml_e2e_summary"]),
        "ml_sklearn_summary": str(ml_required_paths["ml_sklearn_summary"]),
        "ml_window_metrics": str(ml_required_paths["ml_window_metrics"]),
        "ml_portfolio_returns": str(ml_portfolio_returns_path),
    }

    artifacts: dict[str, object] = {
        "ml_e2e_dir": ml_root,
        "artifact_paths": artifact_paths,
        "ml_e2e_summary": ml_e2e_summary,
        "ml_sklearn_summary": ml_sklearn_summary,
        "ml_window_metrics_artifact": ml_window_metrics_artifact,
        "ml_window_metrics": ml_window_metrics,
        "ml_portfolio_returns": ml_portfolio_returns,
        "mom12m_dir": None,
        "mom12m_summary": None,
        "mom12m_portfolio_returns": None,
    }

    if mom12m_dir is not None:
        mom_root = Path(mom12m_dir).expanduser()
        if not mom_root.exists():
            raise FileNotFoundError(f"Mom12m artifact directory does not exist: {mom_root}")

        mom_required_paths = {
            key: mom_root / relative_path for key, relative_path in _MOM12M_REQUIRED_JSON_FILENAMES.items()
        }
        mom_portfolio_returns_path = mom_root / _MOM12M_REQUIRED_PARQUET_FILENAME

        mom12m_summary = _load_required_json_artifact(mom_required_paths["mom12m_summary"])
        mom12m_portfolio_returns = _load_required_parquet_artifact(mom_portfolio_returns_path)

        artifact_paths.update(
            {
                "mom12m_dir": str(mom_root),
                "mom12m_summary": str(mom_required_paths["mom12m_summary"]),
                "mom12m_portfolio_returns": str(mom_portfolio_returns_path),
            }
        )

        artifacts.update(
            {
                "mom12m_dir": mom_root,
                "mom12m_summary": mom12m_summary,
                "mom12m_portfolio_returns": mom12m_portfolio_returns,
            }
        )

    return artifacts


def summarize_window_metrics(window_metrics: list[dict[str, object]] | pd.DataFrame) -> dict[str, object]:
    """Summarize walk-forward window metrics with robust NaN handling."""

    frame = _coerce_window_metrics_frame(window_metrics)
    if frame.empty:
        return {
            "windows": 0,
            "mean_mse": None,
            "median_mse": None,
            "mean_mae": None,
            "median_mae": None,
            "mean_prediction_ic": None,
            "median_prediction_ic": None,
            "mean_prediction_rank_ic": None,
            "median_prediction_rank_ic": None,
            "positive_ic_windows": 0,
            "positive_rank_ic_windows": 0,
            "positive_ic_ratio": None,
            "positive_rank_ic_ratio": None,
            "best_ic_window": None,
            "worst_ic_window": None,
            "best_rank_ic_window": None,
            "worst_rank_ic_window": None,
        }

    numeric = frame.copy()
    for column in _WINDOW_METRIC_COLUMNS:
        if column in numeric.columns:
            numeric[column] = pd.to_numeric(numeric[column], errors="coerce")
        else:
            numeric[column] = np.nan

    ic_values = numeric["prediction_ic"].dropna()
    rank_ic_values = numeric["prediction_rank_ic"].dropna()

    return {
        "windows": int(len(frame)),
        "mean_mse": _safe_series_mean(numeric["mse"]),
        "median_mse": _safe_series_median(numeric["mse"]),
        "mean_mae": _safe_series_mean(numeric["mae"]),
        "median_mae": _safe_series_median(numeric["mae"]),
        "mean_prediction_ic": _safe_series_mean(numeric["prediction_ic"]),
        "median_prediction_ic": _safe_series_median(numeric["prediction_ic"]),
        "mean_prediction_rank_ic": _safe_series_mean(numeric["prediction_rank_ic"]),
        "median_prediction_rank_ic": _safe_series_median(numeric["prediction_rank_ic"]),
        "positive_ic_windows": int((ic_values > 0).sum()),
        "positive_rank_ic_windows": int((rank_ic_values > 0).sum()),
        "positive_ic_ratio": _ratio((ic_values > 0).sum(), len(ic_values)),
        "positive_rank_ic_ratio": _ratio((rank_ic_values > 0).sum(), len(rank_ic_values)),
        "best_ic_window": _select_extreme_window_record(frame, metric_col="prediction_ic", highest=True),
        "worst_ic_window": _select_extreme_window_record(frame, metric_col="prediction_ic", highest=False),
        "best_rank_ic_window": _select_extreme_window_record(
            frame,
            metric_col="prediction_rank_ic",
            highest=True,
        ),
        "worst_rank_ic_window": _select_extreme_window_record(
            frame,
            metric_col="prediction_rank_ic",
            highest=False,
        ),
    }


def summarize_portfolio_returns(
    portfolio_returns: pd.DataFrame,
    *,
    return_col: str = "long_short_ret",
) -> dict[str, object]:
    """Summarize a long-short portfolio return series with deterministic formulas."""

    frame = _prepare_portfolio_returns_frame(portfolio_returns, return_col=return_col)
    if frame.empty:
        return {
            "rows": 0,
            "date_min": None,
            "date_max": None,
            "cumulative_return": None,
            "annualized_return": None,
            "annualized_volatility": None,
            "sharpe": None,
            "mean_monthly_return": None,
            "std_monthly_return": None,
            "positive_month_ratio": None,
            "best_month": None,
            "worst_month": None,
            "max_drawdown": None,
        }

    returns = frame[return_col].to_numpy(dtype=float, copy=True)
    valid_mask = np.isfinite(returns)
    valid_returns = returns[valid_mask]
    valid_frame = frame.loc[valid_mask].copy()
    if valid_frame.empty:
        return {
            "rows": 0,
            "date_min": None,
            "date_max": None,
            "cumulative_return": None,
            "annualized_return": None,
            "annualized_volatility": None,
            "sharpe": None,
            "mean_monthly_return": None,
            "std_monthly_return": None,
            "positive_month_ratio": None,
            "best_month": None,
            "worst_month": None,
            "max_drawdown": None,
        }

    cumulative_factor = float(np.prod(1.0 + valid_returns))
    cumulative_return = cumulative_factor - 1.0

    if cumulative_factor > 0.0:
        annualized_return = float(cumulative_factor ** (12.0 / len(valid_returns)) - 1.0)
    else:
        annualized_return = None

    if len(valid_returns) < 2:
        monthly_std = 0.0
    else:
        monthly_std = float(np.std(valid_returns, ddof=1))
        if not np.isfinite(monthly_std):
            monthly_std = 0.0
    annualized_volatility = float(monthly_std * sqrt(12.0))

    sharpe = None
    if annualized_return is not None and not np.isclose(annualized_volatility, 0.0):
        sharpe = float(annualized_return / annualized_volatility)

    wealth = np.cumprod(1.0 + valid_returns)
    running_peak = np.maximum.accumulate(wealth)
    drawdowns = wealth / running_peak - 1.0
    max_drawdown = float(np.min(drawdowns))

    return {
        "rows": int(len(valid_returns)),
        "date_min": _iso_date(valid_frame["date"].min()),
        "date_max": _iso_date(valid_frame["date"].max()),
        "cumulative_return": json_safe_float(cumulative_return),
        "annualized_return": json_safe_float(annualized_return),
        "annualized_volatility": json_safe_float(annualized_volatility),
        "sharpe": json_safe_float(sharpe),
        "mean_monthly_return": json_safe_float(float(np.mean(valid_returns))),
        "std_monthly_return": json_safe_float(float(monthly_std)),
        "positive_month_ratio": json_safe_float(float((valid_returns > 0).mean())),
        "best_month": json_safe_float(float(np.max(valid_returns))),
        "worst_month": json_safe_float(float(np.min(valid_returns))),
        "max_drawdown": json_safe_float(max_drawdown),
    }


def compare_ml_vs_mom12m(
    ml_portfolio_returns: pd.DataFrame,
    mom12m_portfolio_returns: pd.DataFrame,
    *,
    return_col: str = "long_short_ret",
) -> dict[str, object]:
    """Compare the ML and Mom12m portfolios over overlapping months only."""

    ml_frame = _prepare_portfolio_returns_frame(ml_portfolio_returns, return_col=return_col)
    mom12m_frame = _prepare_portfolio_returns_frame(mom12m_portfolio_returns, return_col=return_col)
    ml_frame = ml_frame.loc[np.isfinite(ml_frame[return_col].to_numpy(dtype=float, copy=False))].reset_index(drop=True)
    mom12m_frame = mom12m_frame.loc[
        np.isfinite(mom12m_frame[return_col].to_numpy(dtype=float, copy=False))
    ].reset_index(drop=True)

    overlap = ml_frame.merge(
        mom12m_frame,
        on="date",
        how="inner",
        suffixes=("_ml", "_mom12m"),
    )
    if overlap.empty:
        raise ValueError("No overlapping dates exist between the ML and Mom12m portfolio returns")

    overlap = overlap.sort_values("date", kind="mergesort").reset_index(drop=True)
    ml_overlap = overlap.loc[:, ["date", f"{return_col}_ml"]].rename(columns={f"{return_col}_ml": return_col})
    mom12m_overlap = overlap.loc[:, ["date", f"{return_col}_mom12m"]].rename(
        columns={f"{return_col}_mom12m": return_col}
    )
    spread_overlap = pd.DataFrame(
        {
            "date": overlap["date"],
            return_col: overlap[f"{return_col}_ml"].to_numpy(dtype=float)
            - overlap[f"{return_col}_mom12m"].to_numpy(dtype=float),
        }
    )

    ml_summary = summarize_portfolio_returns(ml_overlap, return_col=return_col)
    mom12m_summary = summarize_portfolio_returns(mom12m_overlap, return_col=return_col)
    spread_summary = summarize_portfolio_returns(spread_overlap, return_col=return_col)

    ml_returns = ml_overlap[return_col].to_numpy(dtype=float, copy=True)
    mom12m_returns = mom12m_overlap[return_col].to_numpy(dtype=float, copy=True)
    ml_outperformed_months = int((ml_returns > mom12m_returns).sum())

    return {
        "overlap_rows": int(len(overlap)),
        "overlap_date_min": _iso_date(overlap["date"].min()),
        "overlap_date_max": _iso_date(overlap["date"].max()),
        "ml_summary": ml_summary,
        "mom12m_summary": mom12m_summary,
        "spread_summary": spread_summary,
        "ml_cumulative_return": ml_summary["cumulative_return"],
        "mom12m_cumulative_return": mom12m_summary["cumulative_return"],
        "spread_cumulative_return": spread_summary["cumulative_return"],
        "ml_sharpe": ml_summary["sharpe"],
        "mom12m_sharpe": mom12m_summary["sharpe"],
        "spread_mean_monthly_return": spread_summary["mean_monthly_return"],
        "ml_outperformed_months": ml_outperformed_months,
        "ml_outperformed_month_ratio": _ratio(ml_outperformed_months, len(overlap)),
    }


def build_crsp_ml_result_diagnostics(artifacts: dict[str, object]) -> dict[str, object]:
    """Build the diagnostics payload from already-loaded artifacts."""

    ml_e2e_summary = _require_mapping(artifacts, "ml_e2e_summary")
    ml_sklearn_summary = _require_mapping(artifacts, "ml_sklearn_summary")
    ml_window_metrics = artifacts.get("ml_window_metrics")
    ml_portfolio_returns = _require_dataframe(artifacts, "ml_portfolio_returns")
    artifact_paths = dict(artifacts.get("artifact_paths", {}))

    window_diagnostics = summarize_window_metrics(ml_window_metrics if ml_window_metrics is not None else [])
    ml_portfolio_summary = summarize_portfolio_returns(ml_portfolio_returns)

    mom12m_summary = artifacts.get("mom12m_summary")
    mom12m_portfolio_returns = artifacts.get("mom12m_portfolio_returns")
    comparison = None
    if isinstance(mom12m_portfolio_returns, pd.DataFrame):
        comparison = compare_ml_vs_mom12m(ml_portfolio_returns, mom12m_portfolio_returns)

    interpretation = _build_interpretation(
        window_diagnostics=window_diagnostics,
        ml_portfolio_summary=ml_portfolio_summary,
        comparison=comparison,
        mom12m_present=bool(mom12m_summary is not None and isinstance(mom12m_portfolio_returns, pd.DataFrame)),
    )

    diagnostics: dict[str, object] = {
        "title": REPORT_TITLE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ml_e2e_summary": ml_e2e_summary,
        "ml_sklearn_summary": ml_sklearn_summary,
        "window_diagnostics": window_diagnostics,
        "ml_portfolio_summary": ml_portfolio_summary,
        "interpretation": interpretation,
        "limitations": _limitations(),
        "artifact_paths": artifact_paths,
    }
    if mom12m_summary is not None:
        diagnostics["mom12m_summary"] = mom12m_summary
    if comparison is not None:
        diagnostics["comparison"] = comparison

    return _normalize_json_value(diagnostics)


def render_crsp_ml_result_diagnostics_markdown(diagnostics: dict[str, object]) -> str:
    """Render the diagnostics payload as markdown."""

    artifact_paths = diagnostics.get("artifact_paths", {})
    comparison = diagnostics.get("comparison")

    lines = [
        f"# {diagnostics.get('title', REPORT_TITLE)}",
        "",
        f"Generated at: `{_format_text(diagnostics.get('generated_at'))}`",
        "",
        "This diagnostics layer reads existing CRSP ML and Mom12m artifacts. It does not rerun training, rebuild datasets, or change walk-forward splits.",
        "",
        "## Executive Summary",
        _render_markdown_bullets(diagnostics.get("interpretation", [])),
        "",
        "## ML Baseline Summary",
        "### E2E Summary",
        _render_markdown_kv_table(
            diagnostics.get("ml_e2e_summary", {}),
            [
                "dataset_rows",
                "dataset_assets",
                "dataset_date_min",
                "dataset_date_max",
                "walkforward_windows",
                "prediction_rows",
                "prediction_date_min",
                "prediction_date_max",
                "portfolio_rows",
                "portfolio_cumulative_return",
                "portfolio_annualized_return",
                "portfolio_sharpe",
            ],
        ),
        "",
        "### Sklearn Summary",
        _render_markdown_kv_table(
            diagnostics.get("ml_sklearn_summary", {}),
            [
                "model_name",
                "label_col",
                "quantile",
                "random_state",
                "windows",
                "prediction_rows",
                "average_mse",
                "average_mae",
                "average_prediction_ic",
                "average_prediction_rank_ic",
                "portfolio_rows",
                "cumulative_return",
                "annualized_return",
                "sharpe",
            ],
        ),
        "",
        "## Walk-Forward Window Diagnostics",
        _render_markdown_kv_table(
            diagnostics.get("window_diagnostics", {}),
            [
                "windows",
                "mean_mse",
                "median_mse",
                "mean_mae",
                "median_mae",
                "mean_prediction_ic",
                "median_prediction_ic",
                "mean_prediction_rank_ic",
                "median_prediction_rank_ic",
                "positive_ic_windows",
                "positive_rank_ic_windows",
                "positive_ic_ratio",
                "positive_rank_ic_ratio",
            ],
        ),
    ]

    window_diagnostics = diagnostics.get("window_diagnostics", {})
    if any(window_diagnostics.get(key) is not None for key in ("best_ic_window", "worst_ic_window", "best_rank_ic_window", "worst_rank_ic_window")):
        records = [
            _flatten_window_record("best_ic_window", window_diagnostics.get("best_ic_window")),
            _flatten_window_record("worst_ic_window", window_diagnostics.get("worst_ic_window")),
            _flatten_window_record("best_rank_ic_window", window_diagnostics.get("best_rank_ic_window")),
            _flatten_window_record("worst_rank_ic_window", window_diagnostics.get("worst_rank_ic_window")),
        ]
        lines.extend(
            [
                "",
                "### Best and Worst Windows",
                _render_markdown_records_table(
                    records,
                    [
                        "window_type",
                        "window_id",
                        "prediction_ic",
                        "prediction_rank_ic",
                        "mse",
                        "mae",
                    ],
                ),
            ]
        )

    lines.extend(
        [
            "",
            "## Prediction Portfolio",
            _render_markdown_kv_table(
                diagnostics.get("ml_portfolio_summary", {}),
                _PORTFOLIO_SUMMARY_KEYS,
            ),
        ]
    )

    if comparison is not None:
        lines.extend(
            [
                "",
                "## ML vs Mom12m Benchmark Comparison",
                _render_markdown_kv_table(
                    comparison,
                    [
                        "overlap_rows",
                        "overlap_date_min",
                        "overlap_date_max",
                        "ml_cumulative_return",
                        "mom12m_cumulative_return",
                        "spread_cumulative_return",
                        "ml_sharpe",
                        "mom12m_sharpe",
                        "spread_mean_monthly_return",
                        "ml_outperformed_months",
                        "ml_outperformed_month_ratio",
                    ],
                ),
            ]
        )

        lines.extend(
            [
                "",
                "### ML Overlap Portfolio",
                _render_markdown_kv_table(
                    comparison.get("ml_summary", {}),
                    _PORTFOLIO_SUMMARY_KEYS,
                ),
                "",
                "### Mom12m Overlap Portfolio",
                _render_markdown_kv_table(
                    comparison.get("mom12m_summary", {}),
                    _PORTFOLIO_SUMMARY_KEYS,
                ),
                "",
                "### Spread Portfolio",
                _render_markdown_kv_table(
                    comparison.get("spread_summary", {}),
                    _PORTFOLIO_SUMMARY_KEYS,
                ),
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## ML vs Mom12m Benchmark Comparison",
                "Mom12m artifacts were not provided, so no benchmark comparison is included.",
            ]
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            _render_markdown_bullets(diagnostics.get("interpretation", [])),
            "",
            "## Limitations",
            _render_markdown_bullets(diagnostics.get("limitations", [])),
            "",
            "## Artifact Inputs / Outputs",
            _render_markdown_kv_table(
                artifact_paths if isinstance(artifact_paths, dict) else {},
                _sorted_artifact_path_keys(artifact_paths if isinstance(artifact_paths, dict) else {}),
            ),
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def write_crsp_ml_result_diagnostics(
    *,
    ml_e2e_dir: str | Path,
    output_dir: str | Path,
    mom12m_dir: str | Path | None = None,
) -> dict[str, object]:
    """Write diagnostics.json and diagnostics.md for the existing artifacts."""

    artifacts = load_crsp_ml_result_artifacts(ml_e2e_dir=ml_e2e_dir, mom12m_dir=mom12m_dir)
    diagnostics = build_crsp_ml_result_diagnostics(artifacts)

    output_root = Path(output_dir).expanduser()
    output_root.mkdir(parents=True, exist_ok=True)
    diagnostics_json_path = output_root / "diagnostics.json"
    diagnostics_md_path = output_root / "diagnostics.md"

    artifact_paths = dict(diagnostics.get("artifact_paths", {}))
    artifact_paths.update(
        {
            "output_dir": str(output_root),
            "diagnostics_json": str(diagnostics_json_path),
            "diagnostics_md": str(diagnostics_md_path),
        }
    )
    diagnostics = {
        **diagnostics,
        "artifact_paths": artifact_paths,
    }

    diagnostics_md = render_crsp_ml_result_diagnostics_markdown(diagnostics)
    write_json_artifact(diagnostics_json_path, diagnostics)
    diagnostics_md_path.write_text(diagnostics_md, encoding="utf-8")
    return diagnostics


def _load_required_json_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required ML artifact: {path}")
    artifact = load_json_artifact(path)
    if not isinstance(artifact, dict):
        raise TypeError(f"Expected a JSON object in {path}, got {type(artifact).__name__}")
    return artifact


def _load_required_parquet_artifact(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required ML artifact: {path}")
    return read_parquet_artifact(path)


def _require_window_metrics_list(artifact: dict[str, Any], path: Path) -> list[dict[str, object]]:
    window_metrics = artifact.get("window_metrics")
    if not isinstance(window_metrics, list):
        raise TypeError(f"Expected 'window_metrics' to be a list in {path}")
    return window_metrics


def _coerce_window_metrics_frame(window_metrics: list[dict[str, object]] | pd.DataFrame) -> pd.DataFrame:
    if isinstance(window_metrics, pd.DataFrame):
        return window_metrics.copy().reset_index(drop=True)
    if isinstance(window_metrics, list):
        return pd.DataFrame(window_metrics).reset_index(drop=True)
    raise TypeError("window_metrics must be a list of dictionaries or a pandas DataFrame")


def _prepare_portfolio_returns_frame(portfolio_returns: pd.DataFrame, *, return_col: str) -> pd.DataFrame:
    if not isinstance(portfolio_returns, pd.DataFrame):
        raise TypeError("portfolio_returns must be a pandas DataFrame")

    required_columns = {"date", return_col}
    missing = required_columns - set(portfolio_returns.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    frame = portfolio_returns.loc[:, ["date", return_col]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if frame["date"].isna().any():
        raise ValueError("date must be parseable as datetime")
    frame[return_col] = pd.to_numeric(frame[return_col], errors="coerce")
    frame = frame.sort_values("date", kind="mergesort").reset_index(drop=True)
    if frame["date"].duplicated().any():
        raise ValueError("portfolio_returns contains duplicate dates")
    return frame


def _safe_series_mean(values: pd.Series) -> float | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    return json_safe_float(float(numeric.mean()))


def _safe_series_median(values: pd.Series) -> float | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    return json_safe_float(float(numeric.median()))


def _select_extreme_window_record(
    frame: pd.DataFrame,
    *,
    metric_col: str,
    highest: bool,
) -> dict[str, object] | None:
    if metric_col not in frame.columns:
        return None

    numeric = pd.to_numeric(frame[metric_col], errors="coerce")
    numeric = numeric.dropna()
    if numeric.empty:
        return None

    idx = numeric.idxmax() if highest else numeric.idxmin()
    record = frame.loc[idx].to_dict()
    return _normalize_json_value(record)


def _build_interpretation(
    *,
    window_diagnostics: dict[str, object],
    ml_portfolio_summary: dict[str, object],
    comparison: dict[str, object] | None,
    mom12m_present: bool,
) -> list[str]:
    statements: list[str] = []

    mean_ic = window_diagnostics.get("mean_prediction_ic")
    if mean_ic is None:
        statements.append("Average prediction IC is unavailable because no finite window IC values were present.")
    else:
        mean_ic = float(mean_ic)
        if abs(mean_ic) <= 0.02:
            statements.append(
                f"Average prediction IC is {mean_ic:.4f}, which is close to zero and indicates a weak cross-sectional signal."
            )
        elif mean_ic > 0:
            statements.append(f"Average prediction IC is {mean_ic:.4f}, which is positive across the evaluated windows.")
        else:
            statements.append(f"Average prediction IC is {mean_ic:.4f}, which is negative across the evaluated windows.")

    mean_rank_ic = window_diagnostics.get("mean_prediction_rank_ic")
    if mean_rank_ic is None:
        statements.append("Average prediction Rank IC is unavailable because no finite rank-IC values were present.")
    else:
        mean_rank_ic = float(mean_rank_ic)
        if abs(mean_rank_ic) <= 0.02:
            statements.append(
                f"Average prediction Rank IC is {mean_rank_ic:.4f}, which is close to zero and does not show stable ranking skill."
            )
        elif mean_rank_ic < 0:
            statements.append(
                f"Average prediction Rank IC is {mean_rank_ic:.4f}, which suggests unstable or adverse ranking quality."
            )
        else:
            statements.append(
                f"Average prediction Rank IC is {mean_rank_ic:.4f}, which is positive across the evaluated windows."
            )

    cumulative_return = ml_portfolio_summary.get("cumulative_return")
    sharpe = ml_portfolio_summary.get("sharpe")
    if cumulative_return is not None:
        statements.append(
            f"The ML prediction-ranked portfolio cumulative return is {float(cumulative_return):.4f} and its Sharpe ratio is {_format_text(sharpe)}."
        )

    if comparison is None:
        if mom12m_present:
            statements.append("The benchmark comparison could not be built from the available Mom12m artifacts.")
        else:
            statements.append("Mom12m artifacts were not provided, so no benchmark comparison is included.")
        return statements

    ml_cumulative_return = comparison.get("ml_cumulative_return")
    mom12m_cumulative_return = comparison.get("mom12m_cumulative_return")
    if ml_cumulative_return is None or mom12m_cumulative_return is None:
        statements.append("The overlapping-period benchmark comparison is incomplete because one return series has no finite overlap.")
        return statements

    ml_cumulative_return = float(ml_cumulative_return)
    mom12m_cumulative_return = float(mom12m_cumulative_return)
    if ml_cumulative_return > mom12m_cumulative_return:
        statements.append(
            "On the overlapping months, the ML prediction-ranked portfolio outperformed Mom12m on cumulative return."
        )
    elif ml_cumulative_return < mom12m_cumulative_return:
        statements.append(
            "On the overlapping months, the ML prediction-ranked portfolio did not beat Mom12m on cumulative return."
        )
    else:
        statements.append(
            "On the overlapping months, the ML prediction-ranked portfolio matched Mom12m on cumulative return."
        )

    if ml_cumulative_return < mom12m_cumulative_return:
        if mean_ic is not None and abs(float(mean_ic)) <= 0.02:
            statements.append(
                "The overlap result is consistent with a weak prediction signal rather than a strong cross-sectional edge."
            )
        elif mean_rank_ic is not None and float(mean_rank_ic) < 0:
            statements.append(
                "The overlap result is consistent with unstable ranking quality in the prediction ordering."
            )
        else:
            statements.append(
                "The available artifacts do not isolate whether the shortfall is driven by signal quality or portfolio construction."
            )
    elif ml_cumulative_return > mom12m_cumulative_return and cumulative_return is not None:
        statements.append(
            "The ML portfolio summary and the overlap comparison are both positive, which shows the ML portfolio held up on the evaluated date range."
        )

    return statements


def _limitations() -> list[str]:
    return [
        "No transaction costs",
        "No hyperparameter tuning",
        "No cross-sectional preprocessing yet",
        "No feature neutralization",
        "No target clipping",
        "No Compustat fundamentals",
        "No deep learning",
        "Simple equal-weight prediction-ranked portfolio construction if applicable",
        "This report is a presentation layer only; it does not rerun the pipeline",
    ]


def _render_markdown_kv_table(mapping: dict[str, object], keys: list[str]) -> str:
    rows = []
    for key in keys:
        rows.append((key, _format_text(mapping.get(key))))
    return _markdown_table(["Field", "Value"], rows)


def _render_markdown_records_table(records: list[dict[str, object]], keys: list[str]) -> str:
    rows = []
    for record in records:
        rows.append(tuple(_format_text(record.get(key)) for key in keys))
    return _markdown_table([_title_case(key) for key in keys], rows)


def _render_markdown_bullets(items: list[object]) -> str:
    if not items:
        return "- n/a"
    return "\n".join(f"- {_format_text(item)}" for item in items)


def _markdown_table(headers: list[str], rows: list[tuple[str, ...]]) -> str:
    if not rows:
        rows = [tuple("n/a" for _ in headers)]

    header_line = "| " + " | ".join(_escape_markdown_cell(header) for header in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body_lines = []
    for row in rows:
        body_lines.append("| " + " | ".join(_escape_markdown_cell(cell) for cell in row) + " |")
    return "\n".join([header_line, separator, *body_lines])


def _escape_markdown_cell(value: object) -> str:
    text = _format_text(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def _format_text(value: object) -> str:
    if value is None or value is pd.NA:
        return "n/a"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return f"{value:.4f}" if pd.notna(value) else "n/a"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return ", ".join(_format_text(item) for item in value)
    return str(value)


def _title_case(value: str) -> str:
    return value.replace("_", " ").title()


def _sorted_artifact_path_keys(artifact_paths: dict[str, object]) -> list[str]:
    preferred_order = [
        "ml_e2e_dir",
        "ml_e2e_summary",
        "ml_sklearn_summary",
        "ml_window_metrics",
        "ml_portfolio_returns",
        "mom12m_dir",
        "mom12m_summary",
        "mom12m_portfolio_returns",
        "output_dir",
        "diagnostics_json",
        "diagnostics_md",
    ]
    remaining = [key for key in artifact_paths.keys() if key not in preferred_order]
    return [key for key in preferred_order if key in artifact_paths] + sorted(remaining)


def _flatten_window_record(window_type: str, record: dict[str, object] | None) -> dict[str, object]:
    if record is None:
        return {
            "window_type": window_type,
            "window_id": None,
            "prediction_ic": None,
            "prediction_rank_ic": None,
            "mse": None,
            "mae": None,
        }

    flattened = dict(record)
    flattened["window_type"] = window_type
    flattened.setdefault("window_id", None)
    flattened.setdefault("prediction_ic", None)
    flattened.setdefault("prediction_rank_ic", None)
    flattened.setdefault("mse", None)
    flattened.setdefault("mae", None)
    return flattened


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return json_safe_float(float(numerator) / float(denominator))


def _iso_date(value: object) -> str | None:
    if value is None:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed).date().isoformat()


def _require_mapping(artifacts: dict[str, object], key: str) -> dict[str, Any]:
    value = artifacts.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"Expected artifact '{key}' to be a dictionary")
    return value


def _require_dataframe(artifacts: dict[str, object], key: str) -> pd.DataFrame:
    value = artifacts.get(key)
    if not isinstance(value, pd.DataFrame):
        raise TypeError(f"Expected artifact '{key}' to be a pandas DataFrame")
    return value.copy()


def _normalize_json_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, np.generic):
        return _normalize_json_value(value.item())
    if isinstance(value, dict):
        return {str(key): _normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, float):
        return float(value) if pd.notna(value) else None
    if isinstance(value, int):
        return int(value)
    return value
