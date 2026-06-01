"""Momentum baseline helpers for external CRSP monthly panels.

This module builds a classic Mom12m skip-1 signal and a deterministic
long-short portfolio return series from the external monthly panel. It does not
download or commit CRSP data and does not touch ML or backtest semantics.
"""

from __future__ import annotations

import math
from numpy.lib.stride_tricks import sliding_window_view

import numpy as np
import pandas as pd

from .json_utils import json_safe_float


_MOMENTUM_WINDOW = 11
_MOMENTUM_SHIFT = 2


def compute_mom12_1(
    panel: pd.DataFrame,
    *,
    return_col: str = "total_ret",
    min_obs: int = 8,
) -> pd.DataFrame:
    """Compute a monthly Mom12m skip-1 signal for each asset-month.

    The signal uses the prior 11 monthly returns from t-12 through t-2 and
    excludes the most recent month t-1. The calculation is performed per asset
    after sorting by `asset_id` and `date`.
    """
    _validate_momentum_input(panel, return_col=return_col, min_obs=min_obs)

    frame = panel.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if frame["date"].isna().any():
        raise ValueError("date must be parseable as datetime")
    if frame["asset_id"].isna().any():
        raise ValueError("asset_id must be non-null")

    frame = frame.sort_values(["asset_id", "date"], kind="mergesort").reset_index(drop=True)
    frame[return_col] = pd.to_numeric(frame[return_col], errors="coerce")

    mom_values = np.full(len(frame), np.nan, dtype=float)
    for _, asset_frame in frame.groupby("asset_id", sort=False):
        indices = asset_frame.index.to_numpy()
        returns = pd.to_numeric(asset_frame[return_col], errors="coerce").to_numpy(dtype=float, copy=True)
        returns[~np.isfinite(returns)] = np.nan
        mom_values[indices] = _compute_momentum_series(returns, min_obs=min_obs)

    frame["mom12_1"] = mom_values

    preferred_columns = [
        "date",
        "asset_id",
        "permno",
        "ticker",
        return_col,
        "market_cap",
        "lag_market_cap",
        "mom12_1",
    ]
    output_columns = [column for column in preferred_columns if column in frame.columns]
    return frame.loc[:, output_columns].reset_index(drop=True)


def build_momentum_portfolio_returns(
    signal_panel: pd.DataFrame,
    *,
    signal_col: str = "mom12_1",
    return_col: str = "forward_1m_total_ret",
    quantile: float = 0.1,
    weighting: str = "equal",
) -> pd.DataFrame:
    """Build a top-minus-bottom momentum portfolio return series.

    The signal at month t selects the portfolio held over month t+1. If the
    forward return column is not already present, it is derived from `total_ret`
    using a next-month asset shift.
    """
    _validate_portfolio_input(signal_panel, signal_col=signal_col, quantile=quantile, weighting=weighting)

    frame = signal_panel.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if frame["date"].isna().any():
        raise ValueError("date must be parseable as datetime")
    if frame["asset_id"].isna().any():
        raise ValueError("asset_id must be non-null")

    frame = frame.sort_values(["asset_id", "date"], kind="mergesort").reset_index(drop=True)
    frame[signal_col] = pd.to_numeric(frame[signal_col], errors="coerce")

    if return_col in frame.columns:
        frame[return_col] = pd.to_numeric(frame[return_col], errors="coerce")
    else:
        if "total_ret" not in frame.columns:
            raise ValueError(
                f"signal_panel must contain {return_col!r} or a raw total_ret column to derive it"
            )
        frame["total_ret"] = pd.to_numeric(frame["total_ret"], errors="coerce")
        frame[return_col] = frame.groupby("asset_id", sort=False)["total_ret"].shift(-1)

    if weighting == "value" and "lag_market_cap" not in frame.columns:
        raise ValueError("lag_market_cap is required for value-weighted momentum portfolios")
    if weighting == "value":
        frame["lag_market_cap"] = pd.to_numeric(frame["lag_market_cap"], errors="coerce")

    output_rows: list[dict[str, object]] = []
    for date_value, date_frame in frame.groupby("date", sort=True):
        valid_mask = date_frame[signal_col].notna() & date_frame[return_col].notna()
        if not valid_mask.any():
            continue

        ranked = date_frame.loc[valid_mask].copy()
        ranked["_asset_id_sort"] = ranked["asset_id"].astype(str)
        ranked = ranked.sort_values(
            by=[signal_col, "_asset_id_sort"],
            ascending=[True, True],
            kind="mergesort",
        ).reset_index(drop=True)

        side_count = int(math.ceil(len(ranked) * quantile))
        side_count = min(side_count, len(ranked) // 2)
        if side_count < 1:
            continue

        short_frame = ranked.iloc[:side_count].copy()
        long_frame = ranked.iloc[-side_count:].copy()

        if weighting == "equal":
            long_ret = float(long_frame[return_col].mean())
            short_ret = float(short_frame[return_col].mean())
            long_count = int(len(long_frame))
            short_count = int(len(short_frame))
        else:
            long_ret, long_count = _compute_weighted_side_return(long_frame, return_col)
            short_ret, short_count = _compute_weighted_side_return(short_frame, return_col)
            if long_count == 0 or short_count == 0:
                continue

        output_rows.append(
            {
                "date": pd.Timestamp(date_value),
                "long_ret": float(long_ret),
                "short_ret": float(short_ret),
                "long_short_ret": float(long_ret - short_ret),
                "long_count": int(long_count),
                "short_count": int(short_count),
                "weighting": weighting,
                "quantile": float(quantile),
            }
        )

    output_columns = [
        "date",
        "long_ret",
        "short_ret",
        "long_short_ret",
        "long_count",
        "short_count",
        "weighting",
        "quantile",
    ]
    if not output_rows:
        return pd.DataFrame(columns=output_columns)
    return pd.DataFrame(output_rows, columns=output_columns)


def summarize_momentum_returns(portfolio_returns: pd.DataFrame) -> dict[str, object]:
    """Summarize a momentum portfolio return series with deterministic formulas."""
    _validate_summary_input(portfolio_returns)

    frame = portfolio_returns.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if frame["date"].isna().any():
        raise ValueError("date must be parseable as datetime")

    returns = pd.to_numeric(frame["long_short_ret"], errors="coerce").to_numpy(dtype=float, copy=True)
    returns[~np.isfinite(returns)] = np.nan
    valid_returns = returns[~np.isnan(returns)]
    if len(valid_returns) == 0:
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
            "worst_month": None,
            "best_month": None,
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
    annualized_volatility = float(monthly_std * math.sqrt(12.0))
    sharpe = None
    if annualized_return is not None and not math.isclose(annualized_volatility, 0.0):
        sharpe = float(annualized_return / annualized_volatility)

    valid_dates = frame.loc[~np.isnan(returns), "date"]
    return {
        "rows": int(len(valid_returns)),
        "date_min": _iso_date(valid_dates.min()),
        "date_max": _iso_date(valid_dates.max()),
        "cumulative_return": json_safe_float(cumulative_return),
        "annualized_return": json_safe_float(annualized_return),
        "annualized_volatility": json_safe_float(annualized_volatility),
        "sharpe": json_safe_float(sharpe),
        "mean_monthly_return": json_safe_float(float(np.mean(valid_returns))),
        "std_monthly_return": json_safe_float(float(monthly_std)),
        "positive_month_ratio": json_safe_float(float((valid_returns > 0).mean())),
        "worst_month": json_safe_float(float(np.min(valid_returns))),
        "best_month": json_safe_float(float(np.max(valid_returns))),
    }


def _compute_momentum_series(returns: np.ndarray, *, min_obs: int) -> np.ndarray:
    if len(returns) == 0:
        return np.empty(0, dtype=float)

    lookback = np.full(len(returns), np.nan, dtype=float)
    if len(returns) > _MOMENTUM_SHIFT:
        lookback[_MOMENTUM_SHIFT:] = returns[:-_MOMENTUM_SHIFT]

    padded = np.concatenate([np.full(_MOMENTUM_WINDOW - 1, np.nan, dtype=float), lookback])
    windows = sliding_window_view(padded, _MOMENTUM_WINDOW)
    valid = np.isfinite(windows)
    observation_counts = valid.sum(axis=1)
    factors = np.where(valid, 1.0 + windows, 1.0)
    momentum = np.prod(factors, axis=1) - 1.0
    momentum[observation_counts < min_obs] = np.nan
    return momentum.astype(float, copy=False)


def _compute_weighted_side_return(
    side_frame: pd.DataFrame,
    return_col: str,
) -> tuple[float, int]:
    returns = pd.to_numeric(side_frame[return_col], errors="coerce")
    weights = pd.to_numeric(side_frame["lag_market_cap"], errors="coerce")

    valid_mask = returns.notna() & weights.notna() & (weights > 0)
    if not valid_mask.any():
        return float("nan"), 0

    returns = returns.loc[valid_mask].astype(float)
    weights = weights.loc[valid_mask].astype(float)

    weight_sum = float(weights.sum())
    if not np.isfinite(weight_sum) or weight_sum <= 0.0:
        return float("nan"), 0

    normalized_weights = weights / weight_sum
    weighted_return = float((returns * normalized_weights).sum())
    return weighted_return, int(len(returns))


def _validate_momentum_input(panel: pd.DataFrame, *, return_col: str, min_obs: int) -> None:
    if min_obs < 1:
        raise ValueError("min_obs must be >= 1")
    required_columns = ["date", "asset_id", return_col, "market_cap", "lag_market_cap"]
    missing_columns = [column for column in required_columns if column not in panel.columns]
    if missing_columns:
        raise ValueError(f"Missing required momentum input columns: {missing_columns}")


def _validate_portfolio_input(
    signal_panel: pd.DataFrame,
    *,
    signal_col: str,
    quantile: float,
    weighting: str,
) -> None:
    if not 0.0 < quantile <= 0.5:
        raise ValueError("quantile must be in the interval (0, 0.5]")
    if weighting not in {"equal", "value"}:
        raise ValueError("weighting must be either 'equal' or 'value'")

    required_columns = ["date", "asset_id", signal_col]
    missing_columns = [column for column in required_columns if column not in signal_panel.columns]
    if missing_columns:
        raise ValueError(f"Missing required portfolio input columns: {missing_columns}")


def _validate_summary_input(portfolio_returns: pd.DataFrame) -> None:
    required_columns = ["date", "long_short_ret"]
    missing_columns = [column for column in required_columns if column not in portfolio_returns.columns]
    if missing_columns:
        raise ValueError(f"Missing required momentum summary columns: {missing_columns}")


def _iso_date(value: object) -> str | None:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()
