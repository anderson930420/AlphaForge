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
