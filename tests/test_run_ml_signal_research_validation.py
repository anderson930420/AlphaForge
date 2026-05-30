from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ml_signal_research_validation"
SIGNAL_CSV = FIXTURES / "ml_signal.csv"
ALL_FLAT_SIGNAL_CSV = FIXTURES / "all_flat_ml_signal.csv"
MARKET_DATA_CSV = FIXTURES / "market_data.csv"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_ml_signal_research_validation.py"


def _base_args(output_dir: Path, *, signal_file: Path = SIGNAL_CSV, symbol: str = "A") -> list[str]:
    return [
        sys.executable,
        str(SCRIPT),
        "--signal-file",
        str(signal_file),
        "--market-data",
        str(MARKET_DATA_CSV),
        "--symbol",
        symbol,
        "--signal-name",
        "ml_predicted_return",
        "--output-dir",
        str(output_dir),
        "--experiment-name",
        "ml_signal_single_symbol_validation",
        "--development-start",
        "2024-01-31",
        "--development-end",
        "2024-03-31",
        "--holdout-start",
        "2024-04-30",
        "--holdout-end",
        "2024-06-30",
        "--train-size",
        "2",
        "--test-size",
        "1",
        "--step-size",
        "1",
    ]


def _run_script(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )


def _read_summary(output_dir: Path) -> dict[str, object]:
    with open(output_dir / "ml_signal_research_validation_summary.json") as f:
        return json.load(f)


def test_script_projects_single_symbol_and_runs_research_validation(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"

    result = _run_script(_base_args(output_dir))

    assert result.returncode == 0, result.stderr
    derived_signal_path = output_dir / "derived_signal" / "single_symbol_signal.csv"
    assert derived_signal_path.exists()
    derived_signal = pd.read_csv(derived_signal_path)
    assert set(derived_signal["symbol"]) == {"A"}
    assert len(derived_signal) == 6
    assert int((derived_signal["target_weight"].abs() > 0.0).sum()) == 6

    research_summary_path = output_dir / "ml_signal_single_symbol_validation" / "research_protocol_summary.json"
    assert research_summary_path.exists()

    summary = _read_summary(output_dir)
    assert summary["status"] == "ok"
    assert summary["validation_mode"] == "single_symbol_projection"
    assert summary["does_train_model"] is False
    assert summary["does_generate_predictions"] is False
    assert summary["does_add_multi_symbol_backtest"] is False
    assert summary["does_execute_live_trades"] is False
    assert summary["nonzero_target_weight_count"] == 6
    assert summary["all_flat_selected_symbol"] is False
    assert summary["paths"]["research_validation_summary"] == str(research_summary_path)


def test_missing_symbol_fails_fast(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"

    result = _run_script(_base_args(output_dir, symbol="Z"))

    assert result.returncode != 0
    assert "No signal rows found for symbol 'Z'" in result.stderr
    assert not (output_dir / "derived_signal" / "single_symbol_signal.csv").exists()


def test_signal_market_date_mismatch_fails_before_research_validation(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    mismatched_market = tmp_path / "market_data_missing_last_signal_date.csv"
    market_data = pd.read_csv(MARKET_DATA_CSV)
    market_data = market_data.loc[market_data["datetime"] != "2024-06-30"]
    market_data.to_csv(mismatched_market, index=False)

    args = _base_args(output_dir)
    market_data_arg = args.index("--market-data") + 1
    args[market_data_arg] = str(mismatched_market)
    result = _run_script(args)

    assert result.returncode != 0
    assert "Selected signal contains dates not present in market_data" in result.stderr
    assert "2024-06-30" in result.stderr
    assert not (output_dir / "ml_signal_single_symbol_validation" / "research_protocol_summary.json").exists()


def test_all_flat_selected_symbol_warns_but_does_not_fail(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"

    result = _run_script(_base_args(output_dir, signal_file=ALL_FLAT_SIGNAL_CSV))

    assert result.returncode == 0, result.stderr
    assert "selected symbol has zero nonzero target_weight rows" in result.stderr

    summary = _read_summary(output_dir)
    assert summary["nonzero_target_weight_count"] == 0
    assert summary["all_flat_selected_symbol"] is True
    assert summary["warnings"] == [
        "Selected symbol is all-flat under this signal; demo validation may be uninformative."
    ]


def test_multiple_signal_names_require_explicit_signal_name(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    multi_name_signal = tmp_path / "multi_name_signal.csv"
    signal = pd.read_csv(SIGNAL_CSV)
    signal.loc[0, "signal_name"] = "other_signal"
    signal.to_csv(multi_name_signal, index=False)

    args = _base_args(output_dir, signal_file=multi_name_signal)
    signal_name_flag = args.index("--signal-name")
    del args[signal_name_flag : signal_name_flag + 2]
    result = _run_script(args)

    assert result.returncode != 0
    assert "signal.csv contains multiple signal_name values" in result.stderr
    assert "Specify --signal-name explicitly" in result.stderr
