from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from alphaforge.cli import main
from alphaforge.permutation import NULL_MODEL, _permute_market_data_by_blocks, run_permutation_test_with_details
from alphaforge.schemas import (
    BacktestConfig,
    DataSpec,
    ExperimentResult,
    MetricReport,
    PermutationTestArtifactReceipt,
    PermutationTestExecutionOutput,
    PermutationTestSummary,
    StrategySpec,
)
from alphaforge.storage import save_permutation_test_result


def test_return_block_permutation_is_deterministic_and_preserves_datetime_shape() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=5, freq="D"),
            "open": [10.0, 11.0, 12.0, 13.0, 14.0],
            "high": [10.0, 11.0, 12.0, 13.0, 14.0],
            "low": [10.0, 11.0, 12.0, 13.0, 14.0],
            "close": [10.0, 11.0, 12.0, 13.0, 14.0],
            "volume": [100.0, 101.0, 102.0, 103.0, 104.0],
        }
    )

    first = _permute_market_data_by_blocks(market_data, block_size=2, seed=11)
    second = _permute_market_data_by_blocks(market_data, block_size=2, seed=11)

    pd.testing.assert_frame_equal(first, second)
    assert first["datetime"].tolist() == market_data["datetime"].tolist()
    assert first.columns.tolist() == ["datetime", "open", "high", "low", "close", "volume"]
    assert len(first) == len(market_data)
    assert not first[["open", "high", "low", "close", "volume"]].isna().any().any()
    assert np.isfinite(first[["open", "high", "low", "close"]].to_numpy()).all()
    assert (first[["open", "high", "low", "close"]] > 0.0).all().all()


def test_return_block_reconstruction_does_not_stitch_absolute_price_blocks_at_the_anchor() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=4, freq="D"),
            "open": [100.0, 100.0, 1000.0, 1000.0],
            "high": [100.0, 100.0, 1000.0, 1000.0],
            "low": [100.0, 100.0, 1000.0, 1000.0],
            "close": [100.0, 100.0, 1000.0, 1000.0],
            "volume": [100.0, 101.0, 102.0, 103.0],
        }
    )

    reconstructed = _permute_market_data_by_blocks(market_data, block_size=1, seed=0)

    assert reconstructed["close"].iloc[0] == 100.0
    assert reconstructed["close"].iloc[1] == 100.0
    assert reconstructed["datetime"].tolist() == market_data["datetime"].tolist()
    assert reconstructed[["open", "high", "low", "close"]].min().min() > 0.0


def test_return_block_reconstruction_preserves_canonical_market_data_integrity() -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=6, freq="D"),
            "open": [100.0, 101.0, 103.0, 102.0, 105.0, 106.0],
            "high": [102.0, 104.0, 104.0, 106.0, 107.0, 108.0],
            "low": [99.0, 100.0, 101.0, 101.0, 104.0, 105.0],
            "close": [101.0, 103.0, 102.0, 105.0, 106.0, 107.0],
            "volume": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0],
        }
    )

    reconstructed = _permute_market_data_by_blocks(market_data, block_size=2, seed=3)

    assert len(reconstructed) == len(market_data)
    assert reconstructed.columns.tolist() == ["datetime", "open", "high", "low", "close", "volume"]
    assert reconstructed["datetime"].tolist() == market_data["datetime"].tolist()
    assert not reconstructed.isna().any().any()
    assert np.isfinite(reconstructed[["open", "high", "low", "close"]].to_numpy()).all()
    assert (reconstructed[["open", "high", "low", "close"]] > 0.0).all().all()
    assert (reconstructed["high"] >= reconstructed[["open", "low", "close"]].max(axis=1)).all()
    assert (reconstructed["low"] <= reconstructed[["open", "high", "close"]].min(axis=1)).all()


def test_permutation_test_is_deterministic_for_a_fixed_seed(sample_market_csv: Path) -> None:
    data_spec = DataSpec(path=sample_market_csv, symbol="TEST")
    strategy_spec = StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4})

    first = run_permutation_test_with_details(
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        permutation_count=5,
        block_size=2,
        seed=7,
        backtest_config=BacktestConfig(
            initial_capital=1000.0,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
    )
    second = run_permutation_test_with_details(
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        permutation_count=5,
        block_size=2,
        seed=7,
        backtest_config=BacktestConfig(
            initial_capital=1000.0,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
    )

    assert first.permutation_test_summary.target_metric_name == "score"
    assert first.permutation_test_summary.null_model == NULL_MODEL
    assert first.permutation_test_summary.permutation_mode == "block"
    assert first.permutation_test_summary.block_size == 2
    assert first.permutation_test_summary.permutation_metric_values == second.permutation_test_summary.permutation_metric_values
    assert first.permutation_test_summary.empirical_p_value == second.permutation_test_summary.empirical_p_value
    assert first.permutation_test_summary.null_ge_count == second.permutation_test_summary.null_ge_count
    assert len(first.permutation_test_summary.permutation_metric_values) == 5


def test_permutation_test_supports_sharpe_ratio_target_metric(sample_market_csv: Path) -> None:
    summary = run_permutation_test_with_details(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        permutation_count=4,
        block_size=2,
        target_metric_name="sharpe_ratio",
        seed=11,
        backtest_config=BacktestConfig(
            initial_capital=1000.0,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
    ).permutation_test_summary

    assert summary.target_metric_name == "sharpe_ratio"
    assert summary.real_observed_metric_value == pytest.approx(summary.metadata["real_sharpe_ratio"])
    expected_null_ge_count = sum(
        metric_value >= summary.real_observed_metric_value for metric_value in summary.permutation_metric_values
    )
    assert summary.null_ge_count == expected_null_ge_count
    assert summary.empirical_p_value == pytest.approx((expected_null_ge_count + 1) / (summary.permutation_count + 1))


def test_permutation_test_supports_breakout_strategy(sample_market_csv: Path) -> None:
    summary = run_permutation_test_with_details(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="breakout", parameters={"lookback_window": 3}),
        permutation_count=4,
        block_size=2,
        seed=11,
        backtest_config=BacktestConfig(
            initial_capital=1000.0,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
    ).permutation_test_summary

    assert summary.strategy_name == "breakout"
    assert summary.strategy_parameters == {"lookback_window": 3}
    assert len(summary.permutation_metric_values) == 4


def test_permutation_test_with_holdout_cutoff_uses_development_rows_only(sample_market_csv: Path) -> None:
    market_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=8, freq="D"),
            "open": [1.0, 2.0, 3.0, 4.0, 100.0, 101.0, 102.0, 103.0],
            "high": [1.0, 2.0, 3.0, 4.0, 100.0, 101.0, 102.0, 103.0],
            "low": [1.0, 2.0, 3.0, 4.0, 100.0, 101.0, 102.0, 103.0],
            "close": [1.0, 2.0, 3.0, 4.0, 100.0, 101.0, 102.0, 103.0],
            "volume": [1.0] * 8,
        }
    )
    expected_cutoff = pd.Timestamp("2024-01-05")
    dummy_result = ExperimentResult(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        backtest_config=BacktestConfig(1000.0, 0.0, 0.0, 252),
        metrics=MetricReport(0.1, 0.1, 1.0, -0.1, 1.0, 1.0, 1, bar_count=1),
        score=0.9,
    )

    with patch("alphaforge.permutation.load_market_data", return_value=market_data), patch(
        "alphaforge.permutation._evaluate_candidate_on_market_data",
        return_value=dummy_result,
    ) as evaluate_mock:
        summary = run_permutation_test_with_details(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
            permutation_count=2,
            block_size=1,
            holdout_cutoff_date="2024-01-05",
        ).permutation_test_summary

    first_market_data = evaluate_mock.call_args_list[0].kwargs["market_data"]
    assert first_market_data["datetime"].max() < expected_cutoff
    assert summary.metadata["holdout_cutoff_date"] == expected_cutoff.isoformat()
    assert summary.metadata["development_rows"] == 4
    assert summary.metadata["holdout_rows"] == 4


def test_permutation_test_summary_uses_the_empirical_p_value_formula(sample_market_csv: Path) -> None:
    summary = run_permutation_test_with_details(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        permutation_count=4,
        block_size=2,
        seed=11,
        backtest_config=BacktestConfig(
            initial_capital=1000.0,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
    ).permutation_test_summary

    expected_null_ge_count = sum(
        metric_value >= summary.real_observed_metric_value for metric_value in summary.permutation_metric_values
    )
    assert summary.null_ge_count == expected_null_ge_count
    assert summary.empirical_p_value == pytest.approx((expected_null_ge_count + 1) / (summary.permutation_count + 1))


def test_permutation_test_rejects_invalid_block_size(sample_market_csv: Path) -> None:
    with pytest.raises(ValueError, match="block_size"):
        run_permutation_test_with_details(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
            permutation_count=3,
            block_size=0,
        )


def test_permutation_test_rejects_block_size_larger_than_dataset(sample_market_csv: Path) -> None:
    with pytest.raises(ValueError, match="block_size must not exceed"):
        run_permutation_test_with_details(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
            permutation_count=3,
            block_size=999,
        )


def test_permutation_test_rejects_unsupported_target_metric(sample_market_csv: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported permutation target metric"):
        run_permutation_test_with_details(
            data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
            strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
            permutation_count=3,
            block_size=2,
            target_metric_name="total_return",  # type: ignore[arg-type]
        )


def test_save_permutation_test_result_writes_summary_and_score_list(tmp_path: Path) -> None:
    summary = PermutationTestSummary(
        strategy_name="ma_crossover",
        strategy_parameters={"short_window": 2, "long_window": 4},
        target_metric_name="score",
        permutation_mode="block",
        block_size="2",  # type: ignore[arg-type]
        real_observed_metric_value=0.42,
        permutation_metric_values=[0.1, 0.2, 0.3],
        permutation_count="3",  # type: ignore[arg-type]
        seed="11",  # type: ignore[arg-type]
        null_ge_count="1",  # type: ignore[arg-type]
        empirical_p_value=0.5,
        metadata={"source": "unit-test"},
    )

    persisted_summary, receipt = save_permutation_test_result(tmp_path / "permutation_case", summary)

    summary_path = tmp_path / "permutation_case" / "permutation_test_summary.json"
    scores_path = tmp_path / "permutation_case" / "permutation_scores.csv"
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    score_rows = scores_path.read_text(encoding="utf-8").strip().splitlines()

    assert summary_path.exists()
    assert scores_path.exists()
    assert receipt.permutation_test_summary_path == summary_path
    assert receipt.permutation_scores_path == scores_path
    assert persisted_summary.artifact_paths["permutation_test_summary_path"] == str(summary_path)
    assert persisted_summary.artifact_paths["permutation_scores_path"] == str(scores_path)
    assert payload["strategy_name"] == "ma_crossover"
    assert payload["null_model"] == NULL_MODEL
    assert payload["permutation_mode"] == "block"
    assert isinstance(payload["permutation_count"], int)
    assert isinstance(payload["block_size"], int)
    assert payload["block_size"] == 2
    assert isinstance(payload["seed"], int)
    assert isinstance(payload["null_ge_count"], int)
    assert payload["real_observed_metric_value"] == 0.42
    assert payload["permutation_metric_values"] == [0.1, 0.2, 0.3]
    assert payload["artifact_paths"]["permutation_test_summary_path"] == str(summary_path)
    assert payload["artifact_paths"]["permutation_scores_path"] == str(scores_path)
    assert score_rows[0] == "permutation_index,metric_value"
    assert score_rows[1:] == ["1,0.1", "2,0.2", "3,0.3"]


def test_cli_permutation_test_prints_canonical_summary_payload(
    sample_market_csv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphaforge",
            "permutation-test",
            "--data",
            str(sample_market_csv),
            "--output-dir",
            str(tmp_path),
            "--experiment-name",
            "permutation_case",
            "--short-window",
            "2",
            "--long-window",
            "4",
            "--permutations",
            "3",
            "--block-size",
            "2",
            "--target-metric",
            "sharpe_ratio",
            "--seed",
            "11",
        ],
    )

    execution_output = PermutationTestExecutionOutput(
        permutation_test_summary=PermutationTestSummary(
            strategy_name="ma_crossover",
            strategy_parameters={"short_window": 2, "long_window": 4},
            target_metric_name="sharpe_ratio",
            permutation_mode="block",
            block_size=2,
            real_observed_metric_value=0.42,
            permutation_metric_values=[0.1, 0.2, 0.3],
            permutation_count=3,
            seed=11,
            null_ge_count=1,
            empirical_p_value=0.5,
            artifact_paths={
                "permutation_test_summary_path": str(tmp_path / "permutation_case" / "permutation_test_summary.json"),
                "permutation_scores_path": str(tmp_path / "permutation_case" / "permutation_scores.csv"),
            },
            metadata={"source": "unit-test"},
        ),
        artifact_receipt=PermutationTestArtifactReceipt(
            permutation_test_summary_path=tmp_path / "permutation_case" / "permutation_test_summary.json",
            permutation_scores_path=tmp_path / "permutation_case" / "permutation_scores.csv",
        ),
    )

    with patch("alphaforge.cli.run_permutation_test_with_details", return_value=execution_output):
        main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["strategy_name"] == "ma_crossover"
    assert payload["target_metric_name"] == "sharpe_ratio"
    assert payload["null_model"] == NULL_MODEL
    assert payload["permutation_mode"] == "block"
    assert payload["block_size"] == 2
    assert payload["real_observed_metric_value"] == 0.42
    assert payload["permutation_metric_values"] == [0.1, 0.2, 0.3]
    assert payload["empirical_p_value"] == 0.5
    assert payload["permutation_test_summary_path"].endswith("permutation_test_summary.json")
    assert payload["permutation_scores_path"].endswith("permutation_scores.csv")


def test_cli_permutation_test_rejects_invalid_target_metric(
    sample_market_csv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphaforge",
            "permutation-test",
            "--data",
            str(sample_market_csv),
            "--output-dir",
            str(tmp_path),
            "--short-window",
            "2",
            "--long-window",
            "4",
            "--permutations",
            "3",
            "--block-size",
            "2",
            "--target-metric",
            "total_return",
        ],
    )

    with pytest.raises(SystemExit):
        main()


def test_cli_permutation_test_passes_selected_breakout_strategy(
    sample_market_csv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphaforge",
            "permutation-test",
            "--data",
            str(sample_market_csv),
            "--output-dir",
            str(tmp_path),
            "--strategy",
            "breakout",
            "--lookback-window",
            "3",
            "--permutations",
            "3",
            "--block-size",
            "2",
        ],
    )

    execution_output = PermutationTestExecutionOutput(
        permutation_test_summary=PermutationTestSummary(
            strategy_name="breakout",
            strategy_parameters={"lookback_window": 3},
            target_metric_name="score",
            permutation_mode="block",
            block_size=2,
            real_observed_metric_value=0.42,
            permutation_metric_values=[0.1, 0.2, 0.3],
            permutation_count=3,
            seed=42,
            null_ge_count=1,
            empirical_p_value=0.5,
            metadata={"source": "unit-test"},
        ),
        artifact_receipt=None,
    )

    with patch("alphaforge.cli.run_permutation_test_with_details", return_value=execution_output) as mocked_run:
        main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["strategy_name"] == "breakout"
    assert payload["strategy_parameters"] == {"lookback_window": 3}
    assert mocked_run.call_args.kwargs["strategy_spec"] == StrategySpec(
        name="breakout",
        parameters={"lookback_window": 3},
    )
