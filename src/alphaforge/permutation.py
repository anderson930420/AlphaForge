from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import run_backtest
from .data_loader import load_market_data, split_holdout_data
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
NULL_MODEL = "return_block_reconstruction"
PERMUTATION_MODE = "block"
DEFAULT_PERMUTATION_TEST_EXPERIMENT_NAME = "permutation_test"
OHLC_COLUMNS = ("open", "high", "low", "close")
CANONICAL_MARKET_DATA_COLUMNS = ("datetime", "open", "high", "low", "close", "volume")


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
    holdout_cutoff_date: str | None = None,
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
        holdout_cutoff_date=holdout_cutoff_date,
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
    holdout_cutoff_date: str | None = None,
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
    market_data = _apply_holdout_cutoff_if_requested(market_data, holdout_cutoff_date)
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
        null_model=NULL_MODEL,
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
            **_build_holdout_metadata(market_data),
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
    """Build a return-block reconstructed synthetic OHLCV path."""
    _validate_positive_finite_ohlc(market_data)
    if len(market_data) <= 1:
        return market_data.copy().reset_index(drop=True)

    relative_rows = _build_relative_movement_rows(market_data)
    blocks = [relative_rows.iloc[start : start + block_size].copy() for start in range(0, len(relative_rows), block_size)]
    block_order = np.random.default_rng(seed).permutation(len(blocks))
    permuted_blocks = [blocks[index] for index in block_order]
    permuted_relative_rows = pd.concat(permuted_blocks, ignore_index=True)
    return _reconstruct_market_data_from_relative_rows(
        anchor_row=market_data.iloc[0],
        datetimes=market_data["datetime"].reset_index(drop=True),
        relative_rows=permuted_relative_rows,
    )


def _build_relative_movement_rows(market_data: pd.DataFrame) -> pd.DataFrame:
    previous_close = market_data["close"].shift(1)
    relative_rows = pd.DataFrame(
        {
            "open_rel": market_data["open"] / previous_close,
            "high_rel": market_data["high"] / previous_close,
            "low_rel": market_data["low"] / previous_close,
            "close_rel": market_data["close"] / previous_close,
            "volume": market_data["volume"],
        }
    ).iloc[1:].reset_index(drop=True)
    if not np.isfinite(relative_rows[["open_rel", "high_rel", "low_rel", "close_rel"]].to_numpy()).all():
        raise ValueError("Cannot build permutation null from non-finite relative OHLC values")
    if (relative_rows[["open_rel", "high_rel", "low_rel", "close_rel"]] <= 0.0).any().any():
        raise ValueError("Cannot build permutation null from non-positive relative OHLC values")
    return relative_rows


def _reconstruct_market_data_from_relative_rows(
    *,
    anchor_row: pd.Series,
    datetimes: pd.Series,
    relative_rows: pd.DataFrame,
) -> pd.DataFrame:
    rows = [
        {
            "datetime": datetimes.iloc[0],
            "open": float(anchor_row["open"]),
            "high": float(anchor_row["high"]),
            "low": float(anchor_row["low"]),
            "close": float(anchor_row["close"]),
            "volume": float(anchor_row["volume"]),
        }
    ]
    previous_synthetic_close = float(anchor_row["close"])
    for index, relative_row in enumerate(relative_rows.itertuples(index=False), start=1):
        synthetic_open = previous_synthetic_close * float(relative_row.open_rel)
        synthetic_high = previous_synthetic_close * float(relative_row.high_rel)
        synthetic_low = previous_synthetic_close * float(relative_row.low_rel)
        synthetic_close = previous_synthetic_close * float(relative_row.close_rel)
        high = max(synthetic_open, synthetic_high, synthetic_low, synthetic_close)
        low = min(synthetic_open, synthetic_high, synthetic_low, synthetic_close)
        rows.append(
            {
                "datetime": datetimes.iloc[index],
                "open": synthetic_open,
                "high": high,
                "low": low,
                "close": synthetic_close,
                "volume": float(relative_row.volume),
            }
        )
        previous_synthetic_close = synthetic_close
    reconstructed = pd.DataFrame(rows, columns=CANONICAL_MARKET_DATA_COLUMNS)
    _validate_positive_finite_ohlc(reconstructed)
    return reconstructed.reset_index(drop=True)


def _validate_positive_finite_ohlc(market_data: pd.DataFrame) -> None:
    ohlc_values = market_data[list(OHLC_COLUMNS)].astype(float).to_numpy()
    if not np.isfinite(ohlc_values).all():
        raise ValueError("Permutation null construction requires finite OHLC prices")
    if (ohlc_values <= 0.0).any():
        raise ValueError("Permutation null construction requires positive OHLC prices")


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


def _apply_holdout_cutoff_if_requested(
    market_data: pd.DataFrame,
    holdout_cutoff_date: str | None,
) -> pd.DataFrame:
    if holdout_cutoff_date is None:
        return market_data
    development_data, _ = split_holdout_data(market_data, holdout_cutoff_date)
    return development_data


def _build_holdout_metadata(market_data: pd.DataFrame) -> dict[str, object]:
    holdout_cutoff_date = market_data.attrs.get("holdout_cutoff_date")
    if holdout_cutoff_date is None:
        return {}
    return {
        "holdout_cutoff_date": holdout_cutoff_date,
        "development_rows": int(market_data.attrs.get("development_rows", len(market_data))),
        "holdout_rows": int(market_data.attrs.get("holdout_rows", 0)),
    }
