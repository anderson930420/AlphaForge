## Why

SignalForge already produces AlphaForge-compatible `signal.csv`, but there is no deterministic, end-to-end smoke package that shows the full handoff artifact bundle in one place. We need a stable example package that proves SignalForge can export exactly what AlphaForge needs without importing AlphaForge internals or introducing a dependency on AlphaForge.

## What Changes

- Add a deterministic AlphaForge compatibility smoke export package under `examples/alphaforge_compatibility/AAPL_20230101_20241231/`.
- Bundle `market_data.csv`, `signal.csv`, `signal_contract.yaml`, `data_quality_report.json`, `manifest.json`, and `README.md` in that package.
- Add a public export helper for building the smoke package from SignalForge outputs and source market data.
- Ensure the package documents the AlphaForge handoff clearly: SignalForge generates `signal.csv`; AlphaForge validates and backtests it through `custom_signal`.
- Keep the package fully deterministic so it can be used as a stable compatibility fixture and regression target.

## Capabilities

### New Capabilities
- `alphaforge-compatibility-smoke-export`: deterministic compatibility package export for AlphaForge handoff, including bundled market data, signal artifacts, manifest, and package README.

### Modified Capabilities

- None

## Impact

- `src/signalforge/export.py` or a focused export helper module will gain the package export implementation.
- `examples/alphaforge_compatibility/` will gain a committed smoke package fixture.
- Tests will gain end-to-end coverage for package layout, schema alignment, README content, and import boundaries.
- SignalForge remains self-contained and does not gain an AlphaForge dependency.
