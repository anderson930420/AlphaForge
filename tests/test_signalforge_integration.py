from __future__ import annotations

import builtins
import json
from pathlib import Path

import pandas as pd

from alphaforge.custom_signal import load_custom_signal_positions
from alphaforge.data_loader import load_market_data
from alphaforge.experiment_runner import run_research_validation_protocol_with_details
from alphaforge.schemas import (
    BacktestConfig,
    DataSpec,
    ResearchPeriod,
    ResearchValidationConfig,
    ValidationPermutationConfig,
    WalkForwardConfig,
)


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "signalforge"


def test_signalforge_v01_artifacts_run_custom_signal_research_smoke_without_runtime_import(
    tmp_path: Path,
    monkeypatch,
) -> None:
    imported_signalforge_names: list[str] = []
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name.lower().startswith("signalforge"):
            imported_signalforge_names.append(name)
            raise AssertionError(f"AlphaForge must not import SignalForge runtime module {name!r}")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    market_data_path = FIXTURE_ROOT / "market_data.csv"
    signal_path = FIXTURE_ROOT / "signal.csv"

    market_data = load_market_data(DataSpec(path=market_data_path, symbol="SFDEMO"))
    assert market_data["datetime"].dt.strftime("%Y-%m-%d").tolist() == [
        "2025-01-02",
        "2025-01-03",
        "2025-01-06",
        "2025-01-07",
        "2025-01-08",
        "2025-01-09",
        "2025-01-10",
        "2025-01-13",
    ]

    target_positions, signal_metadata = load_custom_signal_positions(
        signal_path,
        market_data,
        symbol="SFDEMO",
        signal_name="signalforge_v01_momentum",
    )

    assert target_positions.tolist() == [1.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0]
    assert signal_metadata["missing_signal_policy"] == "flat"
    assert signal_metadata["signal_name"] == "signalforge_v01_momentum"
    assert signal_metadata["source"] == "SignalForge v0.1"

    execution = run_research_validation_protocol_with_details(
        ResearchValidationConfig(
            data_spec=DataSpec(path=market_data_path, symbol="SFDEMO"),
            strategy_name="custom_signal",
            parameter_grid={},
            development_period=ResearchPeriod(start="2025-01-02", end="2025-01-08"),
            holdout_period=ResearchPeriod(start="2025-01-09", end="2025-01-13"),
            walk_forward_config=WalkForwardConfig(train_size=3, test_size=2, step_size=1),
            backtest_config=BacktestConfig(
                initial_capital=1000.0,
                fee_rate=0.0,
                slippage_rate=0.0,
                annualization_factor=252,
            ),
            permutation_config=ValidationPermutationConfig(enabled=False),
            output_dir=tmp_path,
            experiment_name="signalforge_smoke",
            signal_file=signal_path,
            signal_name="signalforge_v01_momentum",
        )
    )

    summary = execution.research_protocol_summary
    assert summary.selected_strategy == "custom_signal"
    assert summary.selection_rule == "validated_external_signal_file"
    assert summary.development_row_count == 5
    assert summary.holdout_row_count == 3
    assert summary.development_search_summary.result_count == 1
    assert summary.final_holdout_result.strategy_spec.name == "custom_signal"
    assert summary.final_holdout_result.metadata["signal_name"] == "signalforge_v01_momentum"
    assert summary.final_holdout_result.metadata["signal_file"] == str(signal_path)

    assert execution.artifact_receipt is not None
    summary_path = execution.artifact_receipt.research_protocol_summary_path
    persisted_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert persisted_summary["selected_strategy"] == "custom_signal"
    assert (tmp_path / "signalforge_smoke" / "development_signal" / "trade_log.csv").exists()
    assert (tmp_path / "signalforge_smoke" / "final_holdout" / "equity_curve.csv").exists()

    holdout_trade_log = pd.read_csv(tmp_path / "signalforge_smoke" / "final_holdout" / "trade_log.csv")
    assert holdout_trade_log["entry_target_position"].tolist() == [1.0]
    assert holdout_trade_log["exit_target_position"].tolist() == [0.0]
    assert imported_signalforge_names == []
