"""CRSP ML experiment comparison report helpers.

This module compares already-generated CRSP ML experiment artifacts and an
optional Mom12m benchmark artifact. It is a reporting layer only: it does not
rerun training, rebuild datasets, or change model behavior.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .json_utils import json_safe_float, write_json_artifact

REPORT_TYPE = "crsp_ml_experiment_comparison"
REPORT_TITLE = "CRSP ML Experiment Comparison"
_LIMITATIONS = [
    "No transaction costs",
    "No hyperparameter tuning",
    "No industry neutralization",
    "No feature neutralization",
    "No target clipping",
    "No Compustat fundamentals",
    "No live trading or broker integration",
    "This report compares existing artifacts only; it does not rerun experiments",
]
_NEXT_STEPS = [
    "Add transaction-cost and turnover-aware portfolio diagnostics",
    "Tune model hyperparameters inside the walk-forward training loop",
    "Clip or winsorize forward-return targets before supervised learning",
    "Add industry or sector neutralization for features and portfolio weights",
    "Add richer fundamentals when point-in-time Compustat-style data is available",
]
_EXPERIMENT_FIELDS = [
    "name",
    "feature_set",
    "model",
    "average_prediction_ic",
    "average_prediction_rank_ic",
    "cumulative_return",
    "annualized_return",
    "annualized_volatility",
    "sharpe",
    "max_drawdown",
    "portfolio_rows",
    "date_min",
    "date_max",
]


def parse_experiment_arg(value: str) -> tuple[str, Path]:
    """Parse a CLI NAME=DIR experiment argument."""
    if "=" not in value:
        raise ValueError("--experiment must use NAME=DIR format")
    name, raw_dir = value.split("=", 1)
    name = name.strip()
    raw_dir = raw_dir.strip()
    if not name:
        raise ValueError("--experiment name must not be empty")
    if not raw_dir:
        raise ValueError("--experiment directory must not be empty")
    return name, Path(raw_dir)


def load_ml_experiment(name: str, source_dir: str | Path) -> dict[str, object]:
    """Load one CRSP sklearn-style ML experiment directory."""
    root = Path(source_dir)
    summary_path = root / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"ML experiment summary.json is missing: {summary_path}")

    summary = _load_json(summary_path)
    if not isinstance(summary, dict):
        raise ValueError(f"ML experiment summary must be a JSON object: {summary_path}")

    portfolio_path = root / "prediction_portfolio_returns.parquet"
    portfolio_summary = _summarize_optional_portfolio(portfolio_path)

    experiment = {
        "name": name,
        "kind": "ml",
        "model": _first_non_null(summary, "model_name", "model"),
        "feature_set": _infer_feature_set(name=name, summary=summary),
        "average_prediction_ic": _first_float(summary, "average_prediction_ic", "mean_prediction_ic"),
        "average_prediction_rank_ic": _first_float(
            summary,
            "average_prediction_rank_ic",
            "mean_prediction_rank_ic",
        ),
        "cumulative_return": _first_float(summary, "cumulative_return"),
        "annualized_return": _first_float(summary, "annualized_return"),
        "annualized_volatility": _first_float(summary, "annualized_volatility"),
        "sharpe": _first_float(summary, "sharpe"),
        "max_drawdown": _first_float(summary, "max_drawdown"),
        "portfolio_rows": _first_int(summary, "portfolio_rows", "rows"),
        "date_min": _first_non_null(summary, "date_min", "prediction_date_min"),
        "date_max": _first_non_null(summary, "date_max", "prediction_date_max"),
        "source_dir": str(root),
        "summary_path": str(summary_path),
        "portfolio_returns_path": str(portfolio_path) if portfolio_path.exists() else None,
    }

    for key, value in portfolio_summary.items():
        if experiment.get(key) is None:
            experiment[key] = value

    return _normalize_json_value(experiment)


def load_mom12m_benchmark(source_dir: str | Path) -> dict[str, object]:
    """Load an optional Mom12m benchmark directory."""
    root = Path(source_dir)
    summary_path = root / "momentum_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Mom12m momentum_summary.json is missing: {summary_path}")

    summary = _load_json(summary_path)
    if not isinstance(summary, dict):
        raise ValueError(f"Mom12m summary must be a JSON object: {summary_path}")

    portfolio_path = root / "momentum_portfolio_returns.parquet"
    portfolio_summary = _summarize_optional_portfolio(portfolio_path)
    benchmark = {
        "name": "mom12m",
        "kind": "benchmark",
        "cumulative_return": _first_float(summary, "cumulative_return"),
        "annualized_return": _first_float(summary, "annualized_return"),
        "annualized_volatility": _first_float(summary, "annualized_volatility"),
        "sharpe": _first_float(summary, "sharpe"),
        "max_drawdown": _first_float(summary, "max_drawdown"),
        "portfolio_rows": _first_int(summary, "portfolio_rows", "rows"),
        "date_min": _first_non_null(summary, "date_min", "start_date"),
        "date_max": _first_non_null(summary, "date_max", "end_date"),
        "source_dir": str(root),
        "summary_path": str(summary_path),
        "portfolio_returns_path": str(portfolio_path) if portfolio_path.exists() else None,
    }
    for key, value in portfolio_summary.items():
        if benchmark.get(key) is None:
            benchmark[key] = value
    return _normalize_json_value(benchmark)


def build_crsp_ml_experiment_comparison_payload(
    experiments: list[dict[str, object]],
    *,
    benchmark: dict[str, object] | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, object]:
    """Build the deterministic comparison payload."""
    if not experiments:
        raise ValueError("At least one ML experiment is required")

    normalized_experiments = [_normalize_json_value(dict(experiment)) for experiment in experiments]
    normalized_benchmark = _normalize_json_value(benchmark) if benchmark is not None else None
    ranking = build_ranking_summary(normalized_experiments, benchmark=normalized_benchmark)
    interpretation = build_interpretation(normalized_experiments, benchmark=normalized_benchmark, ranking=ranking)

    paths = None
    if output_dir is not None:
        output_root = Path(output_dir)
        paths = {
            "comparison_json": str(output_root / "comparison.json"),
            "comparison_md": str(output_root / "comparison.md"),
        }

    payload = {
        "report_type": REPORT_TYPE,
        "title": REPORT_TITLE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "experiment_count": int(len(normalized_experiments)),
        "experiments": normalized_experiments,
        "benchmark": normalized_benchmark,
        "ranking": ranking,
        "interpretation": interpretation,
        "limitations": list(_LIMITATIONS),
        "next_steps": list(_NEXT_STEPS),
        "output_paths": paths,
    }
    return _normalize_json_value(payload)


def build_crsp_ml_experiment_comparison(
    experiment_specs: list[tuple[str, str | Path]],
    *,
    mom12m_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, object]:
    """Load experiment directories and build the comparison payload."""
    experiments = [load_ml_experiment(name, source_dir) for name, source_dir in experiment_specs]
    benchmark = load_mom12m_benchmark(mom12m_dir) if mom12m_dir is not None else None
    return build_crsp_ml_experiment_comparison_payload(
        experiments,
        benchmark=benchmark,
        output_dir=output_dir,
    )


def build_ranking_summary(
    experiments: list[dict[str, object]],
    *,
    benchmark: dict[str, object] | None = None,
) -> dict[str, object]:
    """Rank experiments by available Rank IC and cumulative return metrics."""
    best_rank_ic = _best_record_name(experiments, "average_prediction_rank_ic")
    best_ic = _best_record_name(experiments, "average_prediction_ic")

    return_candidates: list[dict[str, object]] = [*experiments]
    if benchmark is not None:
        return_candidates.append(benchmark)

    best_cumulative = _best_record_name(return_candidates, "cumulative_return")
    best_ml_cumulative = _best_record_name(experiments, "cumulative_return")

    return {
        "best_by_rank_ic": best_rank_ic,
        "best_by_prediction_ic": best_ic,
        "best_by_cumulative_return": best_cumulative,
        "best_ml_by_cumulative_return": best_ml_cumulative,
    }


def build_interpretation(
    experiments: list[dict[str, object]],
    *,
    benchmark: dict[str, object] | None = None,
    ranking: dict[str, object] | None = None,
) -> list[str]:
    """Build deterministic research interpretation from loaded values only."""
    messages: list[str] = []
    by_name = {str(item.get("name")): item for item in experiments}
    raw = _find_experiment(by_name, feature_set="raw", name_contains="raw")
    rank = _find_experiment(by_name, feature_set="rank", name_contains="rank") or _find_experiment(
        by_name,
        feature_set="xrank",
        name_contains="xrank",
    )

    if raw is not None and rank is not None:
        raw_rank_ic = _to_float(raw.get("average_prediction_rank_ic"))
        rank_rank_ic = _to_float(rank.get("average_prediction_rank_ic"))
        if raw_rank_ic is not None and rank_rank_ic is not None:
            if rank_rank_ic > raw_rank_ic:
                messages.append(
                    "Cross-sectional rank preprocessing improved prediction Rank IC relative to the raw-feature ML baseline."
                )
            elif rank_rank_ic < raw_rank_ic:
                messages.append(
                    "Cross-sectional rank preprocessing did not improve prediction Rank IC relative to the raw-feature ML baseline."
                )
            else:
                messages.append(
                    "Cross-sectional rank preprocessing matched the raw-feature ML baseline on prediction Rank IC."
                )

    if benchmark is not None:
        best_ml = _best_record(experiments, "cumulative_return")
        best_ml_return = _to_float(best_ml.get("cumulative_return")) if best_ml is not None else None
        benchmark_return = _to_float(benchmark.get("cumulative_return"))
        if best_ml_return is not None and benchmark_return is not None:
            if best_ml_return < benchmark_return:
                messages.append(
                    "The best ML cumulative return did not outperform the Mom12m benchmark over the observed comparison window."
                )
            else:
                messages.append(
                    "The best ML cumulative return outperformed the Mom12m benchmark over the observed comparison window, but robustness still requires further validation."
                )

    best_rank_ic_record = _best_record(experiments, "average_prediction_rank_ic")
    best_rank_ic = _to_float(best_rank_ic_record.get("average_prediction_rank_ic")) if best_rank_ic_record else None
    best_ml_return_record = _best_record(experiments, "cumulative_return")
    best_ml_return = _to_float(best_ml_return_record.get("cumulative_return")) if best_ml_return_record else None
    if best_rank_ic is None or abs(best_rank_ic) < 0.01 or best_rank_ic <= 0 or (best_ml_return is not None and best_ml_return <= 0):
        messages.append(
            "The current evidence is not strong enough to claim robust alpha because ranking quality and/or portfolio returns remain weak."
        )

    if ranking:
        best_rank_name = ranking.get("best_by_rank_ic")
        best_return_name = ranking.get("best_by_cumulative_return")
        if best_rank_name is not None and best_return_name is not None and best_rank_name != best_return_name:
            messages.append(
                "The best predictive ranking metric and the best realized portfolio return come from different artifacts, so the research conclusion should stay metric-specific."
            )

    messages.append(
        "Next research steps should prioritize transaction costs, target clipping, feature neutralization, hyperparameter tuning, and richer fundamentals."
    )
    return messages


def render_crsp_ml_experiment_comparison_markdown(payload: dict[str, object]) -> str:
    """Render the comparison payload as a compact Markdown report."""
    lines = [
        f"# {payload.get('title', REPORT_TITLE)}",
        "",
        f"Generated at: `{_format_value(payload.get('generated_at'))}`",
        "",
        "## Summary",
        "",
        "This report compares already-generated CRSP ML experiment artifacts and an optional Mom12m benchmark. It does not rerun training or rebuild datasets.",
        "",
        "## Experiments Compared",
        "",
        _render_experiment_table(payload.get("experiments", [])),
        "",
        "## Benchmark",
        "",
        _render_benchmark_section(payload.get("benchmark")),
        "",
        "## Research Interpretation",
        "",
        _render_bullets(payload.get("interpretation", [])),
        "",
        "## Limitations",
        "",
        _render_bullets(payload.get("limitations", [])),
        "",
        "## Next Steps",
        "",
        _render_bullets(payload.get("next_steps", [])),
        "",
        "## Generated Artifact Paths",
        "",
        _render_paths(payload.get("output_paths")),
    ]
    return "\n".join(lines).strip() + "\n"


def write_crsp_ml_experiment_comparison(
    experiment_specs: list[tuple[str, str | Path]],
    *,
    output_dir: str | Path,
    mom12m_dir: str | Path | None = None,
) -> dict[str, object]:
    """Write comparison.json and comparison.md artifacts."""
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    payload = build_crsp_ml_experiment_comparison(
        experiment_specs,
        mom12m_dir=mom12m_dir,
        output_dir=output_root,
    )
    json_path = output_root / "comparison.json"
    markdown_path = output_root / "comparison.md"
    write_json_artifact(json_path, payload)
    markdown_path.write_text(render_crsp_ml_experiment_comparison_markdown(payload), encoding="utf-8")
    return payload


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _summarize_optional_portfolio(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        frame = pd.read_parquet(path)
    except ImportError:
        raise
    except Exception:
        return {}
    if frame.empty or "long_short_ret" not in frame.columns:
        return {"portfolio_rows": int(len(frame))}

    result: dict[str, object] = {"portfolio_rows": int(len(frame))}
    if "date" in frame.columns:
        dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
        if not dates.empty:
            result["date_min"] = str(dates.min().date())
            result["date_max"] = str(dates.max().date())

    returns = pd.to_numeric(frame["long_short_ret"], errors="coerce").dropna()
    if not returns.empty:
        cumulative = float((1.0 + returns).prod() - 1.0)
        result["cumulative_return"] = cumulative
    return result


def _infer_feature_set(*, name: str, summary: dict[str, object]) -> str | None:
    for key in ("feature_set", "preprocessing", "method"):
        value = summary.get(key)
        if isinstance(value, str) and value:
            return value
    feature_cols = summary.get("feature_cols")
    if isinstance(feature_cols, list) and feature_cols:
        if all(isinstance(col, str) and col.endswith("_xrank") for col in feature_cols):
            return "xrank"
        if any(isinstance(col, str) and col.endswith("_xz") for col in feature_cols):
            return "zscore"
        if any(isinstance(col, str) and col.endswith("_xwz") for col in feature_cols):
            return "winsorized_zscore"
    lowered = name.lower()
    if "winsor" in lowered:
        return "winsorized_zscore"
    if "zscore" in lowered or "_xz" in lowered:
        return "zscore"
    if "xrank" in lowered or "rank" in lowered:
        return "xrank"
    if "raw" in lowered:
        return "raw"
    return None


def _first_non_null(mapping: dict[str, object], *keys: str) -> object | None:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _first_float(mapping: dict[str, object], *keys: str) -> float | None:
    for key in keys:
        value = json_safe_float(mapping.get(key))
        if value is not None:
            return value
    return None


def _first_int(mapping: dict[str, object], *keys: str) -> int | None:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _to_float(value: object) -> float | None:
    return json_safe_float(value)


def _best_record(records: list[dict[str, object]], metric: str) -> dict[str, object] | None:
    valid = [(record, _to_float(record.get(metric))) for record in records]
    valid = [(record, value) for record, value in valid if value is not None]
    if not valid:
        return None
    return max(valid, key=lambda item: item[1])[0]


def _best_record_name(records: list[dict[str, object]], metric: str) -> str | None:
    record = _best_record(records, metric)
    if record is None:
        return None
    name = record.get("name")
    return str(name) if name is not None else None


def _find_experiment(
    by_name: dict[str, dict[str, object]],
    *,
    feature_set: str,
    name_contains: str,
) -> dict[str, object] | None:
    for name, record in by_name.items():
        if str(record.get("feature_set", "")).lower() == feature_set.lower():
            return record
    for name, record in by_name.items():
        if name_contains.lower() in name.lower():
            return record
    return None


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _render_experiment_table(experiments: object) -> str:
    records = experiments if isinstance(experiments, list) else []
    header = "| Experiment | Feature Set | Model | Avg IC | Avg Rank IC | Cumulative Return | Sharpe | Max Drawdown |"
    sep = "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"
    rows = [header, sep]
    for record in records:
        if not isinstance(record, dict):
            continue
        rows.append(
            "| "
            + " | ".join(
                [
                    _format_value(record.get("name")),
                    _format_value(record.get("feature_set")),
                    _format_value(record.get("model")),
                    _format_value(record.get("average_prediction_ic")),
                    _format_value(record.get("average_prediction_rank_ic")),
                    _format_value(record.get("cumulative_return")),
                    _format_value(record.get("sharpe")),
                    _format_value(record.get("max_drawdown")),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _render_benchmark_section(benchmark: object) -> str:
    if not isinstance(benchmark, dict):
        return "No benchmark artifact was provided."
    fields = ["name", "cumulative_return", "annualized_return", "annualized_volatility", "sharpe", "max_drawdown", "portfolio_rows", "date_min", "date_max"]
    return _render_key_value_table(benchmark, fields)


def _render_key_value_table(record: dict[str, object], fields: list[str]) -> str:
    rows = ["| Field | Value |", "| --- | --- |"]
    for field in fields:
        rows.append(f"| `{field}` | {_format_value(record.get(field))} |")
    return "\n".join(rows)


def _render_bullets(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "- None"
    return "\n".join(f"- {_format_value(value)}" for value in values)


def _render_paths(paths: object) -> str:
    if not isinstance(paths, dict) or not paths:
        return "No output paths recorded."
    return _render_key_value_table(paths, list(paths.keys()))


def _normalize_json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool | str | int):
        return value
    if isinstance(value, float):
        return json_safe_float(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_normalize_json_value(item) for item in value]
    return value
