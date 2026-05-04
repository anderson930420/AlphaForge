from __future__ import annotations

"""Minimal research evidence diagnostics for AlphaForge."""

import numpy as np
import pandas as pd

from .backtest import run_backtest
from .metrics import compute_metrics
from .schemas import BacktestConfig, BootstrapEvidenceSummary, CostScenarioSummary, CostSensitivitySummary


LOW_COST_MULTIPLIER = 0.5
HIGH_COST_MULTIPLIER = 2.0


def compute_bootstrap_evidence(
    strategy_returns: pd.Series,
    annualization_factor: int,
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> BootstrapEvidenceSummary:
    returns = pd.Series(strategy_returns, copy=False).astype(float)
    returns = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if returns.empty or len(returns) < 2:
        raise ValueError("bootstrap evidence requires at least two strategy return observations")
    if n_bootstrap <= 0:
        raise ValueError(f"n_bootstrap must be positive, got {n_bootstrap}")
    if annualization_factor <= 0:
        raise ValueError(f"annualization_factor must be positive, got {annualization_factor}")

    values = returns.to_numpy(dtype=float)
    if np.any(values <= -1.0):
        raise ValueError("strategy returns must be greater than -1.0 for bootstrap evidence")

    rng = np.random.default_rng(seed)
    sample_count = int(n_bootstrap)
    observation_count = int(len(values))
    sample_indices = rng.integers(0, observation_count, size=(sample_count, observation_count))
    sampled_returns = values[sample_indices]

    mean_daily_return_samples = sampled_returns.mean(axis=1)
    sample_total_returns = np.prod(1.0 + sampled_returns, axis=1) - 1.0
    annualized_return_samples = (1.0 + sample_total_returns) ** (annualization_factor / observation_count) - 1.0

    mean_daily_return_ci_95 = tuple(
        float(value) for value in np.percentile(mean_daily_return_samples, [2.5, 97.5])
    )
    annualized_return_ci_95 = tuple(
        float(value) for value in np.percentile(annualized_return_samples, [2.5, 97.5])
    )
    ci_crosses_zero = annualized_return_ci_95[0] <= 0.0 <= annualized_return_ci_95[1]
    verdict = "stronger_evidence" if annualized_return_ci_95[0] > 0.0 else "weak_evidence"
    return BootstrapEvidenceSummary(
        n_bootstrap=sample_count,
        seed=int(seed),
        annualized_return_ci_95=annualized_return_ci_95,
        mean_daily_return_ci_95=mean_daily_return_ci_95,
        ci_crosses_zero=ci_crosses_zero,
        verdict=verdict,
    )


def compute_cost_sensitivity(
    *,
    market_data: pd.DataFrame,
    target_positions: pd.Series,
    backtest_config: BacktestConfig,
) -> CostSensitivitySummary:
    if market_data.empty:
        raise ValueError("cost sensitivity requires at least one market data row")
    if len(target_positions) != len(market_data):
        raise ValueError("cost sensitivity target positions must align with market data rows")

    target_positions_series = pd.Series(target_positions, index=market_data.index, dtype=float)
    low_cost = _run_cost_scenario(market_data, target_positions_series, backtest_config, LOW_COST_MULTIPLIER)
    base_cost = _run_cost_scenario(market_data, target_positions_series, backtest_config, 1.0)
    high_cost = _run_cost_scenario(market_data, target_positions_series, backtest_config, HIGH_COST_MULTIPLIER)

    low_acceptable = _is_cost_sensitive_candidate_acceptable(low_cost)
    base_acceptable = _is_cost_sensitive_candidate_acceptable(base_cost)
    high_acceptable = _is_cost_sensitive_candidate_acceptable(high_cost)
    verdict = "cost_fragile" if low_acceptable and (not base_acceptable or not high_acceptable) else "stable"
    return CostSensitivitySummary(low_cost=low_cost, base_cost=base_cost, high_cost=high_cost, verdict=verdict)


def _run_cost_scenario(
    market_data: pd.DataFrame,
    target_positions: pd.Series,
    backtest_config: BacktestConfig,
    multiplier: float,
) -> CostScenarioSummary:
    scenario_config = BacktestConfig(
        initial_capital=backtest_config.initial_capital,
        fee_rate=backtest_config.fee_rate * multiplier,
        slippage_rate=backtest_config.slippage_rate * multiplier,
        annualization_factor=backtest_config.annualization_factor,
    )
    equity_curve, trades = run_backtest(market_data, target_positions, scenario_config)
    metrics = compute_metrics(equity_curve, trades, scenario_config.annualization_factor)
    return CostScenarioSummary(
        annualized_return=float(metrics.annualized_return),
        sharpe=float(metrics.sharpe_ratio),
        max_drawdown=float(metrics.max_drawdown),
    )


def _is_cost_sensitive_candidate_acceptable(summary: CostScenarioSummary) -> bool:
    return summary.annualized_return > 0.0 and summary.sharpe > 0.0
