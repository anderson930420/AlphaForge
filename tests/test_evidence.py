from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from alphaforge.evidence import (
    build_candidate_evidence_summary,
    build_walk_forward_evidence_summary,
    derive_candidate_verdict,
)
from alphaforge.evidence_diagnostics import compute_bootstrap_evidence, compute_cost_sensitivity
from alphaforge.schemas import BacktestConfig, DataSpec, ExperimentResult, MetricReport, SearchSummary, StrategySpec


def _make_result(short_window: int, long_window: int, score: float) -> ExperimentResult:
    return ExperimentResult(
        data_spec=DataSpec(path=Path("sample_data/example.csv"), symbol="2330"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": short_window, "long_window": long_window}),
        backtest_config=BacktestConfig(initial_capital=100000.0, fee_rate=0.001, slippage_rate=0.0005, annualization_factor=252),
        metrics=MetricReport(
            total_return=0.2,
            annualized_return=0.3,
            sharpe_ratio=1.4,
            max_drawdown=-0.08,
            win_rate=0.6,
            turnover=1.2,
            trade_count=4, bar_count=1),
        score=score,
    )


def test_derive_candidate_verdict_covers_small_vocab() -> None:
    assert derive_candidate_verdict(has_search_context=True) == "candidate"
    assert derive_candidate_verdict(has_search_context=True, has_train_metrics=True, has_test_metrics=True) == "validated"
    assert derive_candidate_verdict(has_train_metrics=True, has_test_metrics=True, fold_count=0) == "inconclusive"
    assert derive_candidate_verdict(is_rejected=True) == "rejected"


def test_build_candidate_evidence_summary_records_degradation_and_search_context() -> None:
    best_result = _make_result(2, 4, 0.9)
    search_summary = SearchSummary(
        strategy_name="ma_crossover",
        search_parameter_names=["short_window", "long_window"],
        attempted_combinations=4,
        valid_combinations=4,
        invalid_combinations=0,
        result_count=4,
        ranking_score="score",
        best_result=best_result,
        top_results=[best_result],
    )
    train_result = _make_result(2, 4, 0.9)
    test_result = ExperimentResult(
        data_spec=train_result.data_spec,
        strategy_spec=train_result.strategy_spec,
        backtest_config=train_result.backtest_config,
        metrics=MetricReport(
            total_return=0.1,
            annualized_return=0.12,
            sharpe_ratio=1.1,
            max_drawdown=-0.12,
            win_rate=0.5,
            turnover=0.8,
            trade_count=2, bar_count=1),
        score=0.4,
    )

    evidence = build_candidate_evidence_summary(
        strategy_spec=train_result.strategy_spec,
        train_result=train_result,
        test_result=test_result,
        search_summary=search_summary,
        benchmark_summary={"total_return": 0.05, "max_drawdown": -0.04},
        artifact_paths={"validation_summary_path": "/tmp/validation_summary.json"},
    )

    assert evidence.strategy_name == "ma_crossover"
    assert evidence.strategy_parameters == {"short_window": 2, "long_window": 4}
    assert evidence.verdict == "validated"
    assert evidence.search_rank == 1
    assert evidence.search_result_count == 4
    assert evidence.search_ranking_score == "score"
    assert evidence.search_score == 0.9
    assert evidence.degradation_summary == {
        "return_degradation": -0.18,
        "sharpe_degradation": -0.2999999999999998,
        "max_drawdown_delta": -0.039999999999999994,
    }
    assert evidence.benchmark_relative_summary == {
        "test_total_return": 0.1,
        "benchmark_total_return": 0.05,
        "return_excess": 0.05,
        "test_max_drawdown": -0.12,
        "benchmark_max_drawdown": -0.04,
        "max_drawdown_gap": -0.07999999999999999,
    }
    assert evidence.artifact_paths == {"validation_summary_path": "/tmp/validation_summary.json"}
    assert evidence.cost_sensitivity is None


def test_candidate_evidence_return_degradation_uses_annualized_returns_not_total_returns() -> None:
    train_result = _make_result(2, 4, 0.9)
    test_result = ExperimentResult(
        data_spec=train_result.data_spec,
        strategy_spec=train_result.strategy_spec,
        backtest_config=train_result.backtest_config,
        metrics=MetricReport(
            total_return=0.08,
            annualized_return=0.35,
            sharpe_ratio=1.6,
            max_drawdown=-0.06,
            win_rate=0.6,
            turnover=0.7,
            trade_count=2, bar_count=1),
        score=0.5,
    )

    evidence = build_candidate_evidence_summary(
        strategy_spec=train_result.strategy_spec,
        train_result=train_result,
        test_result=test_result,
        search_summary=None,
        benchmark_summary={"total_return": 0.01, "max_drawdown": -0.04},
    )

    raw_total_return_degradation = test_result.metrics.total_return - train_result.metrics.total_return
    annualized_return_degradation = test_result.metrics.annualized_return - train_result.metrics.annualized_return
    assert raw_total_return_degradation < 0.0
    assert annualized_return_degradation > 0.0
    assert evidence.degradation_summary["return_degradation"] == pytest.approx(annualized_return_degradation)


def test_build_walk_forward_evidence_summary_records_fold_counts_and_artifacts() -> None:
    summary = build_walk_forward_evidence_summary(
        fold_count=3,
        validated_fold_count=3,
        skipped_fold_count=0,
        aggregate_test_metrics={"fold_count": 3, "mean_test_total_return": 0.12},
        aggregate_benchmark_metrics={"fold_count": 3, "mean_benchmark_total_return": 0.08},
        artifact_paths={"walk_forward_summary_path": "/tmp/walk_forward_summary.json", "fold_results_path": "/tmp/fold_results.csv"},
    )

    assert summary.verdict == "validated"
    assert summary.fold_count == 3
    assert summary.validated_fold_count == 3
    assert summary.skipped_fold_count == 0
    assert summary.aggregate_test_metrics == {"fold_count": 3, "mean_test_total_return": 0.12}
    assert summary.aggregate_benchmark_metrics == {"fold_count": 3, "mean_benchmark_total_return": 0.08}
    assert summary.artifact_paths == {
        "walk_forward_summary_path": "/tmp/walk_forward_summary.json",
        "fold_results_path": "/tmp/fold_results.csv",
    }


def test_compute_bootstrap_evidence_is_seed_deterministic() -> None:
    strategy_returns = pd.Series([0.03, -0.01, 0.02, 0.04, 0.01, -0.02, 0.05, 0.0])

    first = compute_bootstrap_evidence(strategy_returns, annualization_factor=252, n_bootstrap=256, seed=7)
    second = compute_bootstrap_evidence(strategy_returns, annualization_factor=252, n_bootstrap=256, seed=7)
    different = compute_bootstrap_evidence(strategy_returns, annualization_factor=252, n_bootstrap=256, seed=8)

    assert first == second
    assert first != different


@pytest.mark.parametrize(
    "strategy_returns,expected_verdict,expected_ci_crosses_zero",
    [
        (pd.Series([0.02, 0.03, 0.04, 0.05, 0.01, 0.025, 0.035, 0.045]), "stronger_evidence", False),
        (pd.Series([0.04, -0.03, 0.0, 0.02, -0.01, 0.01, -0.02, 0.03]), "weak_evidence", True),
    ],
)
def test_compute_bootstrap_evidence_verdict_rules(
    strategy_returns: pd.Series,
    expected_verdict: str,
    expected_ci_crosses_zero: bool,
) -> None:
    evidence = compute_bootstrap_evidence(strategy_returns, annualization_factor=252, n_bootstrap=512, seed=42)

    assert evidence.n_bootstrap == 512
    assert evidence.seed == 42
    assert len(evidence.annualized_return_ci_95) == 2
    assert len(evidence.mean_daily_return_ci_95) == 2
    assert evidence.ci_crosses_zero is expected_ci_crosses_zero
    assert evidence.verdict == expected_verdict
    assert not hasattr(evidence, "cost_sensitivity")


@pytest.mark.parametrize("strategy_returns", [pd.Series(dtype=float), pd.Series([0.01])])
def test_compute_bootstrap_evidence_rejects_insufficient_input(strategy_returns: pd.Series) -> None:
    with pytest.raises(ValueError, match="bootstrap evidence requires at least two strategy return observations"):
        compute_bootstrap_evidence(strategy_returns, annualization_factor=252)


def test_compute_cost_sensitivity_supports_three_scenarios_and_cost_fragile_verdict() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=8, freq="D"),
            "open": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
            "high": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
            "low": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
            "close": [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0],
            "volume": [100.0] * 8,
        }
    )
    target_positions = pd.Series([0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0])
    backtest_config = BacktestConfig(initial_capital=1000.0, fee_rate=0.01, slippage_rate=0.01, annualization_factor=252)

    summary = compute_cost_sensitivity(
        market_data=market_data,
        target_positions=target_positions,
        backtest_config=backtest_config,
    )

    assert summary.verdict == "cost_fragile"
    assert summary.low_cost.annualized_return > summary.base_cost.annualized_return > summary.high_cost.annualized_return
    assert summary.low_cost.max_drawdown >= summary.base_cost.max_drawdown >= summary.high_cost.max_drawdown
    assert summary.low_cost.sharpe > summary.base_cost.sharpe > summary.high_cost.sharpe


def test_compute_cost_sensitivity_stable_when_all_scenarios_pass() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=8, freq="D"),
            "open": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
            "high": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
            "low": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
            "close": [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0],
            "volume": [100.0] * 8,
        }
    )
    target_positions = pd.Series([0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0])
    backtest_config = BacktestConfig(initial_capital=1000.0, fee_rate=0.001, slippage_rate=0.001, annualization_factor=252)

    summary = compute_cost_sensitivity(
        market_data=market_data,
        target_positions=target_positions,
        backtest_config=backtest_config,
    )

    assert summary.verdict == "stable"
    assert summary.low_cost.annualized_return >= summary.base_cost.annualized_return >= summary.high_cost.annualized_return
    assert summary.low_cost.max_drawdown >= summary.base_cost.max_drawdown >= summary.high_cost.max_drawdown


def test_compute_cost_sensitivity_rejects_misaligned_target_positions() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=4, freq="D"),
            "open": [1.0, 2.0, 3.0, 4.0],
            "high": [1.0, 2.0, 3.0, 4.0],
            "low": [1.0, 2.0, 3.0, 4.0],
            "close": [1.0, 2.0, 3.0, 4.0],
            "volume": [1.0, 1.0, 1.0, 1.0],
        }
    )
    target_positions = pd.Series([0.0, 1.0, 0.0])

    with pytest.raises(ValueError, match="cost sensitivity target positions must align with market data rows"):
        compute_cost_sensitivity(
            market_data=market_data,
            target_positions=target_positions,
            backtest_config=BacktestConfig(initial_capital=1000.0, fee_rate=0.01, slippage_rate=0.01, annualization_factor=252),
        )


def test_build_candidate_evidence_summary_attaches_cost_sensitivity_and_bootstrap_evidence() -> None:
    result = _make_result(2, 4, 0.9)
    test_equity_curve = pd.DataFrame({"strategy_return": [0.02, 0.03, 0.01, 0.04], "turnover": [0.1, 0.1, 0.1, 0.1]})
    cost_sensitivity = compute_cost_sensitivity(
        market_data=pd.DataFrame(
            {
                "datetime": pd.date_range("2024-01-01", periods=8, freq="D"),
                "open": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
                "high": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
                "low": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
                "close": [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0],
                "volume": [100.0] * 8,
            }
        ),
        target_positions=pd.Series([0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0]),
        backtest_config=BacktestConfig(initial_capital=1000.0, fee_rate=0.001, slippage_rate=0.001, annualization_factor=252),
    )

    evidence = build_candidate_evidence_summary(
        strategy_spec=result.strategy_spec,
        train_result=result,
        test_result=result,
        test_equity_curve=test_equity_curve,
        search_summary=None,
        benchmark_summary={"total_return": 0.05, "max_drawdown": -0.04},
        cost_sensitivity=cost_sensitivity,
    )

    assert evidence.bootstrap_evidence is not None
    assert evidence.cost_sensitivity is not None
    assert evidence.cost_sensitivity.verdict == "stable"
    assert evidence.bootstrap_evidence.n_bootstrap == 1000
    assert evidence.bootstrap_evidence.seed == 42


def test_build_candidate_evidence_summary_attaches_bootstrap_evidence() -> None:
    result = _make_result(2, 4, 0.9)
    test_equity_curve = pd.DataFrame({"strategy_return": [0.02, 0.03, 0.01, 0.04], "turnover": [0.1, 0.1, 0.1, 0.1]})

    evidence = build_candidate_evidence_summary(
        strategy_spec=result.strategy_spec,
        train_result=result,
        test_result=result,
        test_equity_curve=test_equity_curve,
        search_summary=None,
        benchmark_summary={"total_return": 0.05, "max_drawdown": -0.04},
    )

    assert evidence.bootstrap_evidence is not None
    assert evidence.bootstrap_evidence.n_bootstrap == 1000
    assert evidence.bootstrap_evidence.seed == 42
