## Context

SignalForge already exports the core AlphaForge-compatible signal artifacts: `signal.csv`, `signal_contract.yaml`, and `data_quality_report.json`. What is missing is a deterministic example package that bundles those artifacts together with the matching OHLCV input and a manifest/README that makes the AlphaForge handoff explicit.

The package must stay SignalForge-only. It should not import AlphaForge, should not depend on AlphaForge, and should not attempt to run AlphaForge during tests.

## Goals / Non-Goals

**Goals:**
- Add a deterministic export helper for an AlphaForge compatibility smoke package.
- Bundle `market_data.csv`, `signal.csv`, `signal_contract.yaml`, `data_quality_report.json`, `manifest.json`, and `README.md`.
- Keep the package deterministic and testable as a pure SignalForge export artifact.
- Make the AlphaForge handoff explicit in the package README and manifest.
- Commit a stable example package under `examples/alphaforge_compatibility/AAPL_20230101_20241231/`.

**Non-Goals:**
- No AlphaForge runtime import or dependency.
- No AlphaForge execution, backtesting, or validation call from SignalForge tests.
- No new CLI surface unless later proven necessary.
- No changes to factor logic, signal composition logic, or existing signal schema validation rules beyond package-specific packaging.

## Decisions

### 1. Put the export helper in `src/signalforge/export.py`
`export.py` already owns deterministic artifact writing and layout, so the new smoke-package export helper belongs there rather than in a separate orchestration layer.

Alternatives considered:
- A new `compatibility_package.py` module: cleaner isolation, but adds another public surface without much benefit.
- A CLI-only packaging flow: rejected because the current repo already favors function-level tests and existing generate flow does not need to change.

### 2. Generate the smoke package from provided data frames and existing SignalForge validators
The helper will accept OHLCV market data and the matching signal frame, validate alignment, then write all package files in one deterministic pass.

Alternatives considered:
- Re-running the full CLI pipeline inside the package helper: rejected because that duplicates orchestration and makes the package helper harder to reuse in tests.
- Shelling out to the CLI: rejected because it is less deterministic and harder to test.

### 3. Keep the smoke package deterministic by deriving metadata from the inputs
The package helper will avoid time-of-day nondeterminism by deriving package metadata from the input date range and normalized file content. Hashes will be computed after file generation and excluded from the manifest hash set itself.

Alternatives considered:
- Use `datetime.now()` in export payloads: rejected because it makes the example package unstable across runs.
- Hard-code the manifest without hashes: acceptable fallback, but hashes are easy to compute and make the smoke package more useful.

### 4. Add a committed example package under `examples/alphaforge_compatibility/`
The committed example package will serve as the concrete smoke-test fixture and the thing users can point AlphaForge at directly.

Alternatives considered:
- Generate only in tests: rejected because the task explicitly wants a package that can be copied into AlphaForge and reused.
- Store only a generator script: rejected because the user asked for an actual package layout.

## Risks / Trade-offs

- [Risk] The smoke package could drift from the helper implementation if example files are edited by hand. → Mitigation: generate the committed example package from the same helper and keep regression tests against the committed fixture.
- [Risk] Extra package metadata in `signal_contract.yaml` could look like a schema expansion. → Mitigation: keep the smoke package as a superset of the existing signal contract so existing compatibility checks still pass.
- [Risk] Deterministic hashes depend on normalized serialization. → Mitigation: write package files with UTF-8 and LF line endings and hash the final on-disk bytes.
- [Risk] The package could be mistaken for an AlphaForge dependency. → Mitigation: make the README and manifest state the handoff boundary explicitly and add tests that forbid AlphaForge imports.
