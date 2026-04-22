from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import run_backtest
from .data_loader import load_market_data
from .metrics import compute_metrics
from .search import SUPPORTED_STRATEGY_FAMILIES
from .schemas import (
    BacktestConfig,
    DataSpec,
    ExperimentResult,
    MetricReport,
    PermutationTestExecutionOutput,
    PermutationTestSummary,
    StrategySpec,
    PermutationTargetMetricName,
)
from .scoring import score_metrics
from .storage import save_permutation_test_result
from .strategy.base import Strategy
from .strategy.breakout import BreakoutStrategy
from .strategy.ma_crossover import MovingAverageCrossoverStrategy

SUPPORTED_PERMUTATION_TARGET_METRICS: tuple[PermutationTargetMetricName, ...] = ("score", "sharpe_ratio")
DEFAULT_PERMUTATION_TARGET_METRIC_NAME: PermutationTargetMetricName = "score"
PERMUTATION_MODE = "block"
DEFAULT_PERMUTATION_TEST_EXPERIMENT_NAME = "permutation_test"


def run_permutation_test(
    data_spec: DataSpec,
    strategy_spec: StrategySpec,
    permutation_count: int,
    block_size: int,
    target_metric_name: PermutationTargetMetricName = DEFAULT_PERMUTATION_TARGET_METRIC_NAME,
    seed: int = 42,
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = DEFAULT_PERMUTATION_TEST_EXPERIMENT_NAME,
) -> PermutationTestSummary:
    execution = run_permutation_test_with_details(
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        permutation_count=permutation_count,
        block_size=block_size,
        target_metric_name=target_metric_name,
        seed=seed,
        backtest_config=backtest_config,
        output_dir=output_dir,
        experiment_name=experiment_name,
    )
    return execution.permutation_test_summary


def run_permutation_test_with_details(
    data_spec: DataSpec,
    strategy_spec: StrategySpec,
    permutation_count: int,
    block_size: int,
    target_metric_name: PermutationTargetMetricName = DEFAULT_PERMUTATION_TARGET_METRIC_NAME,
    seed: int = 42,
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = DEFAULT_PERMUTATION_TEST_EXPERIMENT_NAME,
) -> PermutationTestExecutionOutput:
    if permutation_count <= 0:
        raise ValueError("permutation_count must be a positive integer")
    if block_size <= 0:
        raise ValueError("block_size must be a positive integer")
    if target_metric_name not in SUPPORTED_PERMUTATION_TARGET_METRICS:
        supported = ", ".join(SUPPORTED_PERMUTATION_TARGET_METRICS)
        raise ValueError(f"Unsupported permutation target metric: {target_metric_name}. Supported metrics: {supported}")

    backtest_config = backtest_config or _default_backtest_config()
    market_data = load_market_data(data_spec)
    if block_size > len(market_data):
        raise ValueError("block_size must not exceed the number of market data rows")
    real_result = _evaluate_candidate_on_market_data(
        market_data=market_data,
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        backtest_config=backtest_config,
    )
    real_observed_metric_value = _extract_target_metric_value(real_result.metrics, target_metric_name)
    permutation_metric_values = [
        _extract_target_metric_value(
            _evaluate_candidate_on_market_data(
                market_data=_permute_market_data_by_blocks(
                    market_data,
                    block_size=block_size,
                    seed=seed + permutation_index,
                ),
                data_spec=data_spec,
                strategy_spec=strategy_spec,
                backtest_config=backtest_config,
            ).metrics,
            target_metric_name,
        )
        for permutation_index in range(permutation_count)
    ]
    null_ge_count = sum(metric_value >= real_observed_metric_value for metric_value in permutation_metric_values)
    empirical_p_value = (null_ge_count + 1) / (permutation_count + 1)
    summary = PermutationTestSummary(
        strategy_name=strategy_spec.name,
        strategy_parameters=dict(strategy_spec.parameters),
        target_metric_name=target_metric_name,
        permutation_mode=PERMUTATION_MODE,
        block_size=block_size,
        real_observed_metric_value=real_observed_metric_value,
        permutation_metric_values=permutation_metric_values,
        permutation_count=permutation_count,
        seed=seed,
        null_ge_count=null_ge_count,
        empirical_p_value=empirical_p_value,
        metadata={
            "data_rows": len(market_data),
            "real_score": real_result.score,
            "real_total_return": real_result.metrics.total_return,
            "real_sharpe_ratio": real_result.metrics.sharpe_ratio,
            "real_target_metric_name": target_metric_name,
            "real_target_metric_value": real_observed_metric_value,
        },
    )

    artifact_receipt: PermutationTestArtifactReceipt | None = None
    if output_dir is not None:
        workflow_root = _workflow_root(output_dir, experiment_name)
        summary, artifact_receipt = save_permutation_test_result(workflow_root, summary)
    return PermutationTestExecutionOutput(
        permutation_test_summary=summary,
        artifact_receipt=artifact_receipt,
    )


def _evaluate_candidate_on_market_data(
    market_data: pd.DataFrame,
    data_spec: DataSpec,
    strategy_spec: StrategySpec,
    backtest_config: BacktestConfig,
) -> ExperimentResult:
    strategy = _build_strategy(strategy_spec)
    target_positions = strategy.generate_signals(market_data)
    equity_curve, trade_log = run_backtest(market_data, target_positions, backtest_config)
    metrics = compute_metrics(equity_curve, trade_log, backtest_config.annualization_factor)
    return ExperimentResult(
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        backtest_config=backtest_config,
        metrics=metrics,
        score=score_metrics(metrics),
    )


def _extract_target_metric_value(
    metrics: MetricReport,
    target_metric_name: PermutationTargetMetricName,
) -> float:
    if target_metric_name == "score":
        return float(score_metrics(metrics))
    if target_metric_name == "sharpe_ratio":
        return float(metrics.sharpe_ratio)
    raise ValueError(f"Unsupported permutation target metric: {target_metric_name}")


def _permute_market_data_by_blocks(market_data: pd.DataFrame, block_size: int, seed: int) -> pd.DataFrame:
    blocks = [market_data.iloc[start : start + block_size].copy() for start in range(0, len(market_data), block_size)]
    if len(blocks) == 0:
        return market_data.copy().reset_index(drop=True)
    block_order = np.random.default_rng(seed).permutation(len(blocks))
    permuted_blocks = [blocks[index] for index in block_order]
    return pd.concat(permuted_blocks, ignore_index=True)


def _build_strategy(strategy_spec: StrategySpec) -> Strategy:
    if strategy_spec.name == "ma_crossover":
        return MovingAverageCrossoverStrategy(strategy_spec)
    if strategy_spec.name == "breakout":
        return BreakoutStrategy(strategy_spec)
    supported = ", ".join(SUPPORTED_STRATEGY_FAMILIES)
    raise ValueError(f"Unsupported strategy: {strategy_spec.name}. Supported strategies: {supported}")


def _default_backtest_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=100_000.0,
        fee_rate=0.001,
        slippage_rate=0.0005,
        annualization_factor=252,
    )


def _workflow_root(output_dir: Path, experiment_name: str) -> Path:
    return output_dir / experiment_name
