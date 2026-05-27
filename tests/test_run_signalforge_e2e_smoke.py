from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.run_signalforge_e2e_smoke import run_signalforge_e2e_smoke


def _make_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    (path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    return path


def test_signalforge_e2e_smoke_calls_signalforge_then_alphaforge_cli(tmp_path: Path) -> None:
    signalforge_repo = _make_repo(tmp_path / "SignalForge")
    alphaforge_repo = _make_repo(tmp_path / "AlphaForge")
    package_dir = tmp_path / "package"
    calls: list[tuple[list[str], Path | None]] = []

    def fake_runner(command, *, cwd=None, text=True, capture_output=True, check=False, env=None):
        calls.append((list(command), cwd))
        if "signalforge.cli" in command:
            return subprocess.CompletedProcess(command, 0, stdout='{"status":"exported"}\n', stderr="")
        if "alphaforge.cli" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "status": "passed",
                        "package": str(package_dir.resolve()),
                        "market_data_row_count": 4,
                        "signal_row_count": 4,
                        "signal_contract_version": "v0.2",
                        "target_position_source_column": "target_weight",
                        "execution_semantics": "signed_close_to_close_lagged",
                        "equity_curve_rows": 4,
                        "trade_count": 2,
                        "final_equity": 1001.0,
                    }
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command}")

    result = run_signalforge_e2e_smoke(
        signalforge_repo=signalforge_repo,
        alphaforge_repo=alphaforge_repo,
        package_dir=package_dir,
        runner=fake_runner,
    )

    assert result.signalforge_repo == signalforge_repo.resolve()
    assert result.alphaforge_repo == alphaforge_repo.resolve()
    assert result.package_dir == package_dir.resolve()
    assert result.alphaforge_summary["status"] == "passed"
    assert len(calls) == 2

    signalforge_command, signalforge_cwd = calls[0]
    assert signalforge_cwd == signalforge_repo.resolve()
    assert signalforge_command == [
        sys.executable,
        "-m",
        "signalforge.cli",
        "export-alphaforge-v02-smoke",
        "--output-dir",
        str(package_dir.resolve()),
        "--overwrite",
    ]

    alphaforge_command, alphaforge_cwd = calls[1]
    assert alphaforge_cwd == alphaforge_repo.resolve()
    assert alphaforge_command == [
        sys.executable,
        "-m",
        "alphaforge.cli",
        "smoke-signalforge-package",
        "--package",
        str(package_dir.resolve()),
    ]


def test_signalforge_e2e_smoke_rejects_failed_signalforge_command(tmp_path: Path) -> None:
    signalforge_repo = _make_repo(tmp_path / "SignalForge")
    alphaforge_repo = _make_repo(tmp_path / "AlphaForge")

    def fake_runner(command, *, cwd=None, text=True, capture_output=True, check=False, env=None):
        return subprocess.CompletedProcess(command, 3, stdout="", stderr="boom")

    with pytest.raises(RuntimeError, match="Command failed"):
        run_signalforge_e2e_smoke(
            signalforge_repo=signalforge_repo,
            alphaforge_repo=alphaforge_repo,
            package_dir=tmp_path / "package",
            runner=fake_runner,
        )


def test_signalforge_e2e_smoke_rejects_bad_alphaforge_summary(tmp_path: Path) -> None:
    signalforge_repo = _make_repo(tmp_path / "SignalForge")
    alphaforge_repo = _make_repo(tmp_path / "AlphaForge")

    def fake_runner(command, *, cwd=None, text=True, capture_output=True, check=False, env=None):
        if "signalforge.cli" in command:
            return subprocess.CompletedProcess(command, 0, stdout='{"status":"exported"}\n', stderr="")
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "status": "passed",
                    "market_data_row_count": 4,
                    "signal_row_count": 4,
                    "signal_contract_version": "v0.1",
                    "target_position_source_column": "signal_binary",
                    "execution_semantics": "legacy_close_to_close_lagged",
                    "equity_curve_rows": 4,
                    "trade_count": 2,
                    "final_equity": 1001.0,
                }
            ),
            stderr="",
        )

    with pytest.raises(ValueError, match="signal_contract_version"):
        run_signalforge_e2e_smoke(
            signalforge_repo=signalforge_repo,
            alphaforge_repo=alphaforge_repo,
            package_dir=tmp_path / "package",
            runner=fake_runner,
        )


def test_signalforge_e2e_smoke_requires_python_project_paths(tmp_path: Path) -> None:
    signalforge_repo = tmp_path / "SignalForge"
    alphaforge_repo = _make_repo(tmp_path / "AlphaForge")
    signalforge_repo.mkdir()

    with pytest.raises(ValueError, match="does not look like a Python project"):
        run_signalforge_e2e_smoke(
            signalforge_repo=signalforge_repo,
            alphaforge_repo=alphaforge_repo,
            package_dir=tmp_path / "package",
            runner=lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="{}", stderr=""),
        )
