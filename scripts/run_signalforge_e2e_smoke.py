#!/usr/bin/env python3
"""Run SignalForge -> AlphaForge cross-repo CLI smoke.

This script proves the artifact contract between the two repos without importing
SignalForge internals into AlphaForge. It shells out to SignalForge to export a
v0.2 smoke package, then shells out to AlphaForge to consume that package through
`custom_signal v0.2` and `signed_close_to_close_lagged`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


REQUIRED_ALPHAFORGE_SUMMARY = {
    "status": "passed",
    "signal_contract_version": "v0.2",
    "target_position_source_column": "target_weight",
    "execution_semantics": "signed_close_to_close_lagged",
}


class CommandRunner(Protocol):
    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        text: bool = True,
        capture_output: bool = True,
        check: bool = False,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        ...


@dataclass(frozen=True)
class SignalForgeE2ESmokeResult:
    signalforge_repo: Path
    alphaforge_repo: Path
    package_dir: Path
    signalforge_stdout: str
    alphaforge_summary: dict[str, object]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SignalForge -> AlphaForge CLI E2E smoke")
    parser.add_argument("--signalforge-repo", type=Path, required=True, help="Path to the SignalForge repository")
    parser.add_argument(
        "--alphaforge-repo",
        type=Path,
        default=Path.cwd(),
        help="Path to the AlphaForge repository. Defaults to current working directory.",
    )
    parser.add_argument(
        "--package-dir",
        type=Path,
        default=None,
        help="Package output directory. Defaults to a temporary directory.",
    )
    parser.add_argument(
        "--keep-package",
        action="store_true",
        help="Keep the temporary package directory when --package-dir is omitted.",
    )
    return parser


def run_signalforge_e2e_smoke(
    *,
    signalforge_repo: Path,
    alphaforge_repo: Path,
    package_dir: Path,
    runner: CommandRunner = subprocess.run,
) -> SignalForgeE2ESmokeResult:
    signalforge_repo = signalforge_repo.resolve()
    alphaforge_repo = alphaforge_repo.resolve()
    package_dir = package_dir.resolve()

    _validate_repo_path(signalforge_repo, "SignalForge")
    _validate_repo_path(alphaforge_repo, "AlphaForge")
    package_dir.mkdir(parents=True, exist_ok=True)

    signalforge_command = [
        sys.executable,
        "-m",
        "signalforge.cli",
        "export-alphaforge-v02-smoke",
        "--output-dir",
        str(package_dir),
        "--overwrite",
    ]
    signalforge_result = _run_checked(
        runner,
        signalforge_command,
        cwd=signalforge_repo,
        pythonpath_repo=signalforge_repo,
    )

    alphaforge_command = [
        sys.executable,
        "-m",
        "alphaforge.cli",
        "smoke-signalforge-package",
        "--package",
        str(package_dir),
    ]
    alphaforge_result = _run_checked(
        runner,
        alphaforge_command,
        cwd=alphaforge_repo,
        pythonpath_repo=alphaforge_repo,
    )
    alphaforge_summary = _parse_json_stdout(alphaforge_result.stdout, source="AlphaForge smoke CLI")
    _validate_alphaforge_summary(alphaforge_summary)

    return SignalForgeE2ESmokeResult(
        signalforge_repo=signalforge_repo,
        alphaforge_repo=alphaforge_repo,
        package_dir=package_dir,
        signalforge_stdout=signalforge_result.stdout,
        alphaforge_summary=alphaforge_summary,
    )


def _validate_repo_path(path: Path, name: str) -> None:
    if not path.exists() or not path.is_dir():
        raise ValueError(f"{name} repo path does not exist or is not a directory: {path}")
    if not (path / "pyproject.toml").exists():
        raise ValueError(f"{name} repo path does not look like a Python project: {path}")


def _run_checked(
    runner: CommandRunner,
    command: Sequence[str],
    *,
    cwd: Path,
    pythonpath_repo: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    result = runner(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=_build_subprocess_env(pythonpath_repo),
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Command failed\n"
            f"cwd: {cwd}\n"
            f"command: {' '.join(command)}\n"
            f"exit_code: {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def _build_subprocess_env(pythonpath_repo: Path | None) -> dict[str, str] | None:
    if pythonpath_repo is None:
        return None
    env = os.environ.copy()
    src_path = str((pythonpath_repo / "src").resolve())
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        src_path if not existing_pythonpath else src_path + os.pathsep + existing_pythonpath
    )
    return env


def _parse_json_stdout(stdout: str, *, source: str) -> dict[str, object]:
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source} did not print valid JSON: {exc}\nstdout:\n{stdout}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{source} JSON output must be an object")
    return parsed


def _validate_alphaforge_summary(summary: dict[str, object]) -> None:
    for key, expected in REQUIRED_ALPHAFORGE_SUMMARY.items():
        actual = summary.get(key)
        if actual != expected:
            raise ValueError(f"AlphaForge smoke summary {key!r} must be {expected!r}, got {actual!r}")

    positive_int_fields = ("market_data_row_count", "signal_row_count", "equity_curve_rows")
    for field in positive_int_fields:
        value = summary.get(field)
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"AlphaForge smoke summary {field!r} must be a positive integer, got {value!r}")

    if not isinstance(summary.get("trade_count"), int):
        raise ValueError("AlphaForge smoke summary 'trade_count' must be an integer")
    if not isinstance(summary.get("final_equity"), (float, int)):
        raise ValueError("AlphaForge smoke summary 'final_equity' must be numeric")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.package_dir is not None:
        result = run_signalforge_e2e_smoke(
            signalforge_repo=args.signalforge_repo,
            alphaforge_repo=args.alphaforge_repo,
            package_dir=args.package_dir,
        )
        print(json.dumps(_result_summary(result), indent=2, sort_keys=True))
        return 0

    with tempfile.TemporaryDirectory(prefix="signalforge-e2e-smoke-") as temp_dir:
        package_dir = Path(temp_dir) / "package"
        result = run_signalforge_e2e_smoke(
            signalforge_repo=args.signalforge_repo,
            alphaforge_repo=args.alphaforge_repo,
            package_dir=package_dir,
        )
        print(json.dumps(_result_summary(result), indent=2, sort_keys=True))
        if args.keep_package:
            print("--keep-package is ignored when --package-dir is omitted because TemporaryDirectory owns cleanup.", file=sys.stderr)
        return 0


def _result_summary(result: SignalForgeE2ESmokeResult) -> dict[str, object]:
    return {
        "status": "passed",
        "signalforge_repo": str(result.signalforge_repo),
        "alphaforge_repo": str(result.alphaforge_repo),
        "package_dir": str(result.package_dir),
        "alphaforge_summary": result.alphaforge_summary,
    }


if __name__ == "__main__":
    raise SystemExit(main())
