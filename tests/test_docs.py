from __future__ import annotations

from pathlib import Path


def test_signalforge_readiness_report_exists_and_names_core_terms() -> None:
    report_path = Path(__file__).resolve().parents[1] / "docs" / "releases" / "signalforge-integration-readiness.md"

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
