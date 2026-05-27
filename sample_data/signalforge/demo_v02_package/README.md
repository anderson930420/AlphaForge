# SignalForge v0.2 Demo Package

This is a deterministic sample package produced in the SignalForge artifact format and consumed by AlphaForge.

It is intentionally small and does not contain real market data.

## Files

- `market_data.csv`
- `signal.csv`
- `signal_contract.yaml`
- `data_quality_report.json`
- `manifest.json`
- `README.md`

## AlphaForge Smoke Command

```bash
PYTHONPATH=src python3 -m alphaforge.cli smoke-signalforge-package \
  --package sample_data/signalforge/demo_v02_package
```

## Expected Semantics

- Strategy: `custom_signal`
- Signal contract: `v0.2`
- Position source: `target_weight`
- Execution semantics: `signed_close_to_close_lagged`

## Boundary

AlphaForge consumes this package as files only. It does not import SignalForge internals.
