from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from alphaforge.experiment_runner import run_experiment, run_search
from alphaforge.schemas import BacktestConfig, DataSpec, StrategySpec


def test_run_experiment_saves_outputs(sample_market_csv: Path, tmp_path: Path) -> None:
    result, equity_curve, trades = run_experiment(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(
            name="ma_crossover",
            parameters={"short_window": 2, "long_window": 3},
        ),
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="runner_case",
    )

    assert result.metrics_path is not None
    assert result.trade_log_path is not None
    assert result.equity_curve_path is not None
    assert result.metrics.trade_count >= 0
    assert not equity_curve.empty
    assert isinstance(trades, pd.DataFrame)


def test_run_experiment_saved_artifacts_match_returned_metrics_and_trades(
    sample_market_csv: Path,
    tmp_path: Path,
) -> None:
    result, _, trades = run_experiment(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(
            name="ma_crossover",
            parameters={"short_window": 2, "long_window": 3},
        ),
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="artifact_match_case",
    )

    metrics_payload = json.loads((tmp_path / "artifact_match_case" / "metrics_summary.json").read_text(encoding="utf-8"))
    trade_log_frame = pd.read_csv(tmp_path / "artifact_match_case" / "trade_log.csv")

    assert metrics_payload["trade_count"] == result.metrics.trade_count
    assert metrics_payload["turnover"] == result.metrics.turnover
    assert metrics_payload["total_return"] == result.metrics.total_return
    assert len(trade_log_frame) == len(trades)
    assert trade_log_frame.columns.tolist() == trades.columns.tolist()


def test_run_search_ranks_multiple_parameter_sets(sample_market_csv: Path, tmp_path: Path) -> None:
    ranked = run_search(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"short_window": [2, 3], "long_window": [4, 5]},
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="search_case",
    )

    assert len(ranked) == 4
    assert ranked[0].score >= ranked[-1].score
    assert (tmp_path / "search_case" / "ranked_results.csv").exists()


def test_run_search_saves_ranked_results_and_per_run_artifacts_under_search_root(
    sample_market_csv: Path,
    tmp_path: Path,
) -> None:
    ranked = run_search(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"short_window": [2, 3], "long_window": [4]},
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="search_layout_case",
    )

    search_root = tmp_path / "search_layout_case"
    runs_root = search_root / "runs"

    assert len(ranked) == 2
    assert (search_root / "ranked_results.csv").exists()
    assert (runs_root / "run_001" / "experiment_config.json").exists()
    assert (runs_root / "run_001" / "metrics_summary.json").exists()
    assert (runs_root / "run_001" / "trade_log.csv").exists()
    assert (runs_root / "run_001" / "equity_curve.csv").exists()
    assert (runs_root / "run_002" / "experiment_config.json").exists()


def test_run_search_saves_empty_ranked_results_with_headers(sample_market_csv: Path, tmp_path: Path) -> None:
    ranked = run_search(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        parameter_grid={"short_window": [2], "long_window": [4]},
        backtest_config=BacktestConfig(
            initial_capital=1000,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
        output_dir=tmp_path,
        experiment_name="filtered_search_case",
        min_trade_count=10,
    )

    ranked_path = tmp_path / "filtered_search_case" / "ranked_results.csv"
    ranked_frame = pd.read_csv(ranked_path)

    assert ranked == []
    assert ranked_path.exists()
    assert ranked_frame.empty
    assert ranked_frame.columns.tolist() == [
        "strategy",
        "short_window",
        "long_window",
        "total_return",
        "annualized_return",
        "sharpe_ratio",
        "max_drawdown",
        "win_rate",
        "turnover",
        "trade_count",
        "score",
    ]
