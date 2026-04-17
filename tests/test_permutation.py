from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from alphaforge.cli import main
from alphaforge.permutation import run_permutation_test_with_details
from alphaforge.schemas import (
    BacktestConfig,
    DataSpec,
    PermutationTestArtifactReceipt,
    PermutationTestExecutionOutput,
    PermutationTestSummary,
    StrategySpec,
)
from alphaforge.storage import save_permutation_test_result


def test_permutation_test_is_deterministic_for_a_fixed_seed(sample_market_csv: Path) -> None:
    data_spec = DataSpec(path=sample_market_csv, symbol="TEST")
    strategy_spec = StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4})

    first = run_permutation_test_with_details(
        data_spec=data_spec,
        strategy_spec=strategy_spec,
        permutation_count=5,
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
        seed=7,
        backtest_config=BacktestConfig(
            initial_capital=1000.0,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
    )

    assert first.permutation_test_summary.target_metric_name == "score"
    assert first.permutation_test_summary.permutation_scores == second.permutation_test_summary.permutation_scores
    assert first.permutation_test_summary.empirical_p_value == second.permutation_test_summary.empirical_p_value
    assert first.permutation_test_summary.null_ge_count == second.permutation_test_summary.null_ge_count
    assert len(first.permutation_test_summary.permutation_scores) == 5


def test_permutation_test_summary_uses_the_empirical_p_value_formula(sample_market_csv: Path) -> None:
    summary = run_permutation_test_with_details(
        data_spec=DataSpec(path=sample_market_csv, symbol="TEST"),
        strategy_spec=StrategySpec(name="ma_crossover", parameters={"short_window": 2, "long_window": 4}),
        permutation_count=4,
        seed=11,
        backtest_config=BacktestConfig(
            initial_capital=1000.0,
            fee_rate=0.0,
            slippage_rate=0.0,
            annualization_factor=252,
        ),
    ).permutation_test_summary

    expected_null_ge_count = sum(score >= summary.real_observed_score for score in summary.permutation_scores)
    assert summary.null_ge_count == expected_null_ge_count
    assert summary.empirical_p_value == pytest.approx((expected_null_ge_count + 1) / (summary.permutation_count + 1))


def test_save_permutation_test_result_writes_summary_and_score_list(tmp_path: Path) -> None:
    summary = PermutationTestSummary(
        strategy_name="ma_crossover",
        strategy_parameters={"short_window": 2, "long_window": 4},
        target_metric_name="score",
        real_observed_score=0.42,
        permutation_scores=[0.1, 0.2, 0.3],
        permutation_count=3,
        seed=11,
        null_ge_count=1,
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
    assert payload["real_observed_score"] == 0.42
    assert payload["artifact_paths"]["permutation_test_summary_path"] == str(summary_path)
    assert payload["artifact_paths"]["permutation_scores_path"] == str(scores_path)
    assert score_rows[0] == "permutation_index,score"
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
            "--seed",
            "11",
        ],
    )

    execution_output = PermutationTestExecutionOutput(
        permutation_test_summary=PermutationTestSummary(
            strategy_name="ma_crossover",
            strategy_parameters={"short_window": 2, "long_window": 4},
            target_metric_name="score",
            real_observed_score=0.42,
            permutation_scores=[0.1, 0.2, 0.3],
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
    assert payload["target_metric_name"] == "score"
    assert payload["real_observed_score"] == 0.42
    assert payload["permutation_scores"] == [0.1, 0.2, 0.3]
    assert payload["empirical_p_value"] == 0.5
    assert payload["permutation_test_summary_path"].endswith("permutation_test_summary.json")
    assert payload["permutation_scores_path"].endswith("permutation_scores.csv")
