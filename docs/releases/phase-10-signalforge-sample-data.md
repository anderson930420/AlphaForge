# Phase 10 SignalForge Sample Data Package

## Summary

This phase adds a deterministic SignalForge v0.2 sample package under AlphaForge `sample_data/`.

The sample package is intentionally small and does not contain real market data. Its purpose is to give AlphaForge a stable consumer-side fixture for SignalForge package compatibility.

## Path

```text
sample_data/signalforge/demo_v02_package/
```

## Files

```text
market_data.csv
signal.csv
signal_contract.yaml
data_quality_report.json
manifest.json
README.md
```

## Verification

```bash
PYTHONPATH=src python3 -m alphaforge.cli smoke-signalforge-package \
  --package sample_data/signalforge/demo_v02_package
```

Expected semantics:

```text
signal_contract_version = v0.2
target_position_source_column = target_weight
execution_semantics = signed_close_to_close_lagged
```

## Boundary

AlphaForge consumes this package as files only. It does not import SignalForge internals.

Real market data workflows should stay documented or generated from SignalForge, rather than committed as large third-party data files.
