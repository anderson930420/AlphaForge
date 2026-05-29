from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class FactorDiagnosticsResult:
    summary: dict[str, Any]
    coverage_by_date: pd.DataFrame
    distribution_by_date: pd.DataFrame
    ic_by_date: pd.DataFrame
    quantile_returns: pd.DataFrame
    long_short_spread: pd.DataFrame


def load_supervised_panel(path: Path | str) -> pd.DataFrame:
    """Load a supervised factor-label panel from CSV or Parquet."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported supervised panel suffix: {suffix}")


def run_factor_diagnostics(
    panel: pd.DataFrame,
    *,
    factor_col: str,
    label_col: str = "ret_fwd_1m",
    asset_id_col: str = "asset_id",
    date_col: str = "date",
    quantiles: int = 5,
) -> FactorDiagnosticsResult:
    """Compute single-factor asset-pricing diagnostics from a supervised panel.

    The diagnostics evaluate the factor as a cross-sectional signal rather than
    as a trading strategy. They are intentionally model-free: coverage,
    distribution, IC/rank-IC, quantile forward returns, and long-short spread.
    """
    if quantiles < 2:
        raise ValueError("quantiles must be at least 2")
    _require_columns(panel, [asset_id_col, date_col, factor_col, label_col])

    frame = panel[[asset_id_col, date_col, factor_col, label_col]].copy()
    frame[asset_id_col] = frame[asset_id_col].astype(str)
    frame[date_col] = _to_month_end(frame[date_col])
    frame[factor_col] = pd.to_numeric(frame[factor_col], errors="coerce")
    frame[label_col] = pd.to_numeric(frame[label_col], errors="coerce")
    frame = frame.sort_values([date_col, asset_id_col]).reset_index(drop=True)

    coverage = build_coverage_by_date(frame, factor_col=factor_col, date_col=date_col)
    distribution = build_distribution_by_date(frame, factor_col=factor_col, date_col=date_col)
    ic = build_ic_by_date(frame, factor_col=factor_col, label_col=label_col, date_col=date_col)
    quantile_returns = build_quantile_returns(
        frame,
        factor_col=factor_col,
        label_col=label_col,
        date_col=date_col,
        quantiles=quantiles,
    )
    spread = build_long_short_spread(quantile_returns, quantiles=quantiles)
    summary = build_factor_summary(
        frame,
        factor_col=factor_col,
        label_col=label_col,
        asset_id_col=asset_id_col,
        date_col=date_col,
        quantiles=quantiles,
        coverage=coverage,
        ic=ic,
        spread=spread,
    )

    return FactorDiagnosticsResult(
        summary=summary,
        coverage_by_date=coverage,
        distribution_by_date=distribution,
        ic_by_date=ic,
        quantile_returns=quantile_returns,
        long_short_spread=spread,
    )


def build_coverage_by_date(frame: pd.DataFrame, *, factor_col: str, date_col: str) -> pd.DataFrame:
    rows = []
    for date, group in frame.groupby(date_col, sort=True):
        asset_count = int(len(group))
        valid_factor_count = int(group[factor_col].notna().sum())
        missing_factor_count = asset_count - valid_factor_count
        coverage_ratio = valid_factor_count / asset_count if asset_count else float("nan")
        rows.append({
            "date": date,
            "asset_count": asset_count,
            "valid_factor_count": valid_factor_count,
            "missing_factor_count": missing_factor_count,
            "coverage_ratio": coverage_ratio,
        })
    return pd.DataFrame(rows)


def build_distribution_by_date(frame: pd.DataFrame, *, factor_col: str, date_col: str) -> pd.DataFrame:
    rows = []
    for date, group in frame.groupby(date_col, sort=True):
        values = group[factor_col].dropna()
        rows.append({
            "date": date,
            "count": int(values.count()),
            "mean": _safe_float(values.mean()),
            "std": _safe_float(values.std(ddof=1)),
            "min": _safe_float(values.min()),
            "median": _safe_float(values.median()),
            "max": _safe_float(values.max()),
        })
    return pd.DataFrame(rows)


def build_ic_by_date(
    frame: pd.DataFrame,
    *,
    factor_col: str,
    label_col: str,
    date_col: str,
) -> pd.DataFrame:
    rows = []
    for date, group in frame.groupby(date_col, sort=True):
        valid = group[[factor_col, label_col]].dropna()
        rows.append({
            "date": date,
            "row_count": int(len(valid)),
            "ic": _corr(valid[factor_col], valid[label_col]),
            "rank_ic": _corr(valid[factor_col].rank(method="average"), valid[label_col].rank(method="average")),
        })
    return pd.DataFrame(rows)


def build_quantile_returns(
    frame: pd.DataFrame,
    *,
    factor_col: str,
    label_col: str,
    date_col: str,
    quantiles: int,
) -> pd.DataFrame:
    rows = []
    for date, group in frame.groupby(date_col, sort=True):
        valid = group[[factor_col, label_col]].dropna().copy()
        if len(valid) < quantiles or valid[factor_col].nunique(dropna=True) < 2:
            continue
        ranks = valid[factor_col].rank(method="first")
        try:
            valid["quantile"] = pd.qcut(ranks, q=quantiles, labels=False) + 1
        except ValueError:
            continue
        for quantile, qgroup in valid.groupby("quantile", sort=True):
            rows.append({
                "date": date,
                "quantile": f"Q{int(quantile)}",
                "quantile_number": int(quantile),
                "asset_count": int(len(qgroup)),
                "mean_forward_return": _safe_float(qgroup[label_col].mean()),
                "median_forward_return": _safe_float(qgroup[label_col].median()),
            })
    return pd.DataFrame(rows)


def build_long_short_spread(quantile_returns: pd.DataFrame, *, quantiles: int) -> pd.DataFrame:
    if quantile_returns.empty:
        return pd.DataFrame(columns=["date", "long_quantile", "short_quantile", "long_short_spread"])

    rows = []
    for date, group in quantile_returns.groupby("date", sort=True):
        high = group[group["quantile_number"] == quantiles]
        low = group[group["quantile_number"] == 1]
        if high.empty or low.empty:
            continue
        rows.append({
            "date": date,
            "long_quantile": f"Q{quantiles}",
            "short_quantile": "Q1",
            "long_short_spread": _safe_float(high["mean_forward_return"].iloc[0] - low["mean_forward_return"].iloc[0]),
        })
    return pd.DataFrame(rows)


def build_factor_summary(
    frame: pd.DataFrame,
    *,
    factor_col: str,
    label_col: str,
    asset_id_col: str,
    date_col: str,
    quantiles: int,
    coverage: pd.DataFrame,
    ic: pd.DataFrame,
    spread: pd.DataFrame,
) -> dict[str, Any]:
    ic_values = ic["ic"].dropna() if "ic" in ic else pd.Series(dtype=float)
    rank_ic_values = ic["rank_ic"].dropna() if "rank_ic" in ic else pd.Series(dtype=float)
    spread_values = spread["long_short_spread"].dropna() if "long_short_spread" in spread else pd.Series(dtype=float)

    return {
        "factor_col": factor_col,
        "label_col": label_col,
        "asset_id_col": asset_id_col,
        "date_col": date_col,
        "quantiles": quantiles,
        "row_count": int(len(frame)),
        "date_count": int(frame[date_col].nunique()),
        "asset_count": int(frame[asset_id_col].nunique()),
        "mean_coverage_ratio": _safe_float(coverage["coverage_ratio"].mean()) if not coverage.empty else None,
        "ic_observation_count": int(len(ic_values)),
        "ic_mean": _safe_float(ic_values.mean()),
        "ic_std": _safe_float(ic_values.std(ddof=1)),
        "ic_t_stat": _t_stat(ic_values),
        "rank_ic_observation_count": int(len(rank_ic_values)),
        "rank_ic_mean": _safe_float(rank_ic_values.mean()),
        "rank_ic_std": _safe_float(rank_ic_values.std(ddof=1)),
        "rank_ic_t_stat": _t_stat(rank_ic_values),
        "long_short_observation_count": int(len(spread_values)),
        "long_short_spread_mean": _safe_float(spread_values.mean()),
        "long_short_spread_std": _safe_float(spread_values.std(ddof=1)),
    }


def write_factor_diagnostics(
    result: FactorDiagnosticsResult,
    output_dir: Path | str,
) -> dict[str, str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "factor_summary": output_dir / "factor_summary.json",
        "factor_coverage_by_date": output_dir / "factor_coverage_by_date.csv",
        "factor_distribution_by_date": output_dir / "factor_distribution_by_date.csv",
        "factor_ic_timeseries": output_dir / "factor_ic_timeseries.csv",
        "factor_quantile_returns": output_dir / "factor_quantile_returns.csv",
        "factor_long_short_spread": output_dir / "factor_long_short_spread.csv",
    }

    with open(paths["factor_summary"], "w") as f:
        json.dump(result.summary, f, indent=2, default=str)
    result.coverage_by_date.to_csv(paths["factor_coverage_by_date"], index=False)
    result.distribution_by_date.to_csv(paths["factor_distribution_by_date"], index=False)
    result.ic_by_date.to_csv(paths["factor_ic_timeseries"], index=False)
    result.quantile_returns.to_csv(paths["factor_quantile_returns"], index=False)
    result.long_short_spread.to_csv(paths["factor_long_short_spread"], index=False)

    return {name: str(path) for name, path in paths.items()}


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _to_month_end(values: pd.Series) -> pd.Series:
    dates = pd.to_datetime(values, errors="coerce")
    if dates.isna().all():
        raise ValueError("date column has no valid dates")
    return dates.dt.to_period("M").dt.to_timestamp("M")


def _corr(left: pd.Series, right: pd.Series) -> float | None:
    if len(left) < 2 or left.nunique(dropna=True) < 2 or right.nunique(dropna=True) < 2:
        return None
    value = left.corr(right)
    return _safe_float(value)


def _t_stat(values: pd.Series) -> float | None:
    clean = values.dropna()
    if len(clean) < 2:
        return None
    std = clean.std(ddof=1)
    if pd.isna(std) or std == 0:
        return None
    return _safe_float(clean.mean() / (std / (len(clean) ** 0.5)))


def _safe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
