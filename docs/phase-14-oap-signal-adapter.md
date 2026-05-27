# Phase 14 OAP Signal Adapter

## Summary

Phase 14 adds a contract-driven OAP / JKP signal adapter.

The adapter converts a normalized Phase 13 factor frame into the existing AlphaForge v0.2 signal schema.

## Input

The input is a normalized factor frame with these columns:

```text
datetime
available_at
symbol
asset_id
factor_name
factor_value
source
```

## Output

The output is the existing AlphaForge v0.2 signal shape:

```text
datetime
available_at
symbol
signal_name
score
direction
target_weight
source
```

## Threshold rule

Phase 14 supports the Phase 12 threshold subset.

```text
factor_value > long_threshold  -> direction = 1
factor_value < short_threshold -> direction = -1
otherwise                      -> direction = 0
```

For signed unit weighting:

```text
direction = 1  -> long_weight
direction = -1 -> short_weight
direction = 0  -> neutral_weight
```

## Boundary

This phase only maps normalized factors into v0.2 signal rows. It does not download OAP / JKP data, run backtests, add optimization, add cross-sectional ranking rules, change ML behavior, change runtime semantics, or change the v0.2 signal schema.

## Verification

```bash
PYTHONPATH=src python3 -m pytest tests/test_oap_signal_adapter.py tests/test_oap_loader.py tests/test_oap_factor_contract.py -q
PYTHONPATH=src python3 -m pytest -q
```
