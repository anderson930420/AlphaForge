from __future__ import annotations

from pathlib import Path

import pandas as pd

from .backtest import run_backtest
from .data_loader import load_market_data
from .metrics import compute_metrics
from .schemas import (
    BacktestConfig,
    DataSpec,
    ExperimentResult,
    PermutationTestExecutionOutput,
    PermutationTestSummary,
    StrategySpec,
)
from .scoring import score_metrics
from .storage import save_permutation_test_result
from .strategy.ma_crossover import MovingAverageCrossoverStrategy

TARGET_METRIC_NAME = "score"
DEFAULT_PERMUTATION_TEST_EXPERIMENT_NAME = "permutation_test"


def run_permutation_test(
    data_spec: DataSpec,
    strategy_spec: StrategySpec,
    permutation_count: int,
    seed: int = 42,
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = DEFAULT_PERMUTATION_TEST_EXPERIMENT_NAME,
) -> PermutationTestSummary:
    execution = run_permutation_test_with_details(
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        permutation_count=permutation_count,
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
    seed: int = 42,
    backtest_config: BacktestConfig | None = None,
    output_dir: Path | None = None,
    experiment_name: str = DEFAULT_PERMUTATION_TEST_EXPERIMENT_NAME,
) -> PermutationTestExecutionOutput:
    if permutation_count <= 0:
        raise ValueError("permutation_count must be a positive integer")

    backtest_config = backtest_config or _default_backtest_config()
    market_data = load_market_data(data_spec)
    real_result = _evaluate_candidate_on_market_data(
        market_data=market_data,
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        backtest_config=backtest_config,
    )
    permutation_scores = [
        _evaluate_candidate_on_market_data(
            market_data=_permute_market_data(market_data, seed=seed + permutation_index),
            data_spec=data_spec,
            strategy_spec=strategy_spec,
            backtest_config=backtest_config,
        ).score
        for permutation_index in range(permutation_count)
    ]
    null_ge_count = sum(score >= real_result.score for score in permutation_scores)
    empirical_p_value = (null_ge_count + 1) / (permutation_count + 1)
    summary = PermutationTestSummary(
        strategy_name=strategy_spec.name,
        strategy_parameters=dict(strategy_spec.parameters),
        target_metric_name=TARGET_METRIC_NAME,
        real_observed_score=real_result.score,
        permutation_scores=permutation_scores,
        permutation_count=permutation_count,
        seed=seed,
        null_ge_count=null_ge_count,
        empirical_p_value=empirical_p_value,
        metadata={
            "data_rows": len(market_data),
            "real_total_return": real_result.metrics.total_return,
            "real_sharpe_ratio": real_result.metrics.sharpe_ratio,
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


def _permute_market_data(market_data: pd.DataFrame, seed: int) -> pd.DataFrame:
    return market_data.sample(frac=1.0, replace=False, random_state=seed).reset_index(drop=True)


def _build_strategy(strategy_spec: StrategySpec) -> MovingAverageCrossoverStrategy:
    if strategy_spec.name != "ma_crossover":
        raise ValueError(f"Unsupported strategy: {strategy_spec.name}")
    return MovingAverageCrossoverStrategy(strategy_spec)


def _default_backtest_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=100_000.0,
        fee_rate=0.001,
        slippage_rate=0.0005,
        annualization_factor=252,
    )


def _workflow_root(output_dir: Path, experiment_name: str) -> Path:
    return output_dir / experiment_name
