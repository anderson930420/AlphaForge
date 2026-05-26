from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_signalforge_readiness_report_exists_and_names_core_terms() -> None:
    report_path = ROOT / "docs" / "releases" / "signalforge-integration-readiness.md"

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")

    for expected_text in (
        "SignalForge",
        "custom_signal",
        "signal_binary",
        "target_position",
        "ruff check",
        "READY",
    ):
        assert expected_text in content


def test_signalforge_docs_name_custom_signal_walk_forward_limitation() -> None:
    doc_paths = (
        ROOT / "docs" / "signalforge_integration.md",
        ROOT / "docs" / "releases" / "signalforge-integration-readiness.md",
    )

    for doc_path in doc_paths:
        content = doc_path.read_text(encoding="utf-8").lower()

        assert "frozen external signal" in content
        assert "does not perform parameter search" in content
        assert ("fold_count` 0" in content) or ("no walk-forward folds" in content)


def test_signalforge_docs_name_daily_datetime_policy() -> None:
    content = (ROOT / "docs" / "signalforge_integration.md").read_text(encoding="utf-8").lower()

    assert "daily trading-date" in content
    assert "does not utc-shift" in content
    assert "does not perform intraday timing validation" in content


def test_signalforge_docs_name_v02_signal_semantics_boundary() -> None:
    content = (ROOT / "docs" / "signalforge_integration.md").read_text(encoding="utf-8").lower()

    assert "signal semantics v0.2" in content
    assert "target_weight" in content
    assert "direction" in content
    assert "current_weight -> target_weight" in content
    assert "do not yet alter the v0.1 `custom_signal` runtime behavior" in content


def test_phase_2_signal_adapter_doc_names_target_weight_boundary() -> None:
    content = (ROOT / "docs" / "releases" / "phase-2-v02-signal-adapter.md").read_text(encoding="utf-8")

    assert "v0.2 `signal.csv`" in content
    assert "target_weight" in content
    assert "target_position" in content
    assert "between `0.0` and `1.0`" in content
    assert "silently clipped" in content


def test_phase_3_signed_runtime_doc_names_execution_boundary() -> None:
    content = (ROOT / "docs" / "releases" / "phase-3-signed-backtest-runtime.md").read_text(encoding="utf-8")

    assert "signed_close_to_close_lagged" in content
    assert "legacy_close_to_close_lagged" in content
    assert "[-1.0, 1.0]" in content
    assert "strategy_return[t] = position[t] * close_return[t]" in content
    assert "Existing CLI paths still call the default legacy runtime" in content
