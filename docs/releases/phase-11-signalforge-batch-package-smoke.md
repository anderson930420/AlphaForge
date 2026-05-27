# Phase 11 SignalForge Batch Package Smoke

## Summary

This phase adds a script-level batch smoke workflow for multiple SignalForge v0.2 packages.

It wraps the existing single-package SignalForge compatibility smoke and writes one JSON summary across all discovered packages.

## Command

```bash
PYTHONPATH=src python3 scripts/run_signalforge_batch_package_smoke.py \
  --packages-root ../SignalForge/artifacts/tw_multi_symbol/packages \
  --summary-output artifacts/signalforge_batch_smoke_summary.json
```

## Input Shape

```text
packages/
  2330.TW/
    market_data.csv
    signal.csv
    signal_contract.yaml
    data_quality_report.json
    manifest.json
    README.md
  0050.TW/
    ...
```

## Output Summary

The script prints JSON and can also write it to `--summary-output`.

Important fields:

```text
status
package_count
passed_count
failed_count
packages[]
```

Each package entry includes:

```text
status
package
market_data_row_count
signal_row_count
signal_contract_version
target_position_source_column
execution_semantics
equity_curve_rows
trade_count
final_equity
```

## Boundary

This phase does not change the AlphaForge runtime or SignalForge package contract.

AlphaForge consumes package files only and does not import SignalForge internals.
