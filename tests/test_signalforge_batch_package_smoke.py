from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.run_signalforge_batch_package_smoke import (
    discover_signalforge_v02_package_dirs,
    run_signalforge_batch_package_smoke,
)


SAMPLE_PACKAGE = Path("sample_data/signalforge/demo_v02_package")
SCRIPT = Path("scripts/run_signalforge_batch_package_smoke.py")


def _copy_sample_package(destination: Path) -> None:
    shutil.copytree(SAMPLE_PACKAGE, destination)


def test_discover_signalforge_v02_package_dirs_accepts_single_package() -> None:
    assert discover_signalforge_v02_package_dirs(SAMPLE_PACKAGE) == [SAMPLE_PACKAGE]


def test_discover_signalforge_v02_package_dirs_finds_child_packages(tmp_path: Path) -> None:
    packages_root = tmp_path / "packages"
    _copy_sample_package(packages_root / "A")
    _copy_sample_package(packages_root / "B")
    (packages_root / "not_a_package").mkdir()

    assert discover_signalforge_v02_package_dirs(packages_root) == [packages_root / "A", packages_root / "B"]


def test_discover_signalforge_v02_package_dirs_rejects_empty_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No SignalForge v0.2 package directories"):
        discover_signalforge_v02_package_dirs(tmp_path)


def test_run_signalforge_batch_package_smoke_summarizes_multiple_packages(tmp_path: Path) -> None:
    packages_root = tmp_path / "packages"
    _copy_sample_package(packages_root / "2330.TW")
    _copy_sample_package(packages_root / "0050.TW")

    summary = run_signalforge_batch_package_smoke(packages_root)

    assert summary["status"] == "passed"
    assert summary["package_count"] == 2
    assert summary["passed_count"] == 2
    assert summary["failed_count"] == 0
    assert [Path(entry["package"]).name for entry in summary["packages"]] == ["0050.TW", "2330.TW"]
    for entry in summary["packages"]:
        assert entry["status"] == "passed"
        assert entry["signal_contract_version"] == "v0.2"
        assert entry["target_position_source_column"] == "target_weight"
        assert entry["execution_semantics"] == "signed_close_to_close_lagged"
        assert entry["equity_curve_rows"] == 4
        assert entry["trade_count"] == 2
        assert isinstance(entry["final_equity"], float)


def test_batch_script_writes_summary_output(tmp_path: Path) -> None:
    packages_root = tmp_path / "packages"
    _copy_sample_package(packages_root / "2330.TW")
    summary_output = tmp_path / "summary" / "batch_summary.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--packages-root",
            str(packages_root),
            "--summary-output",
            str(summary_output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    stdout_summary = json.loads(completed.stdout)
    file_summary = json.loads(summary_output.read_text(encoding="utf-8"))
    assert stdout_summary == file_summary
    assert file_summary["status"] == "passed"
    assert file_summary["package_count"] == 1
