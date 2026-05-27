# Phase 13 OAP Loader

## Summary

Phase 13 adds a local OAP / JKP factor loader that normalizes raw characteristic CSV files according to the Phase 12 factor contract.

## Files

- `src/alphaforge/oap_loader.py`
- `tests/test_oap_loader.py`

## Output frame

The normalized factor frame contains:

```text
datetime
available_at
symbol
asset_id
factor_name
factor_value
source
```

## Policy support

Phase 13 supports the Phase 12 timing subset:

```text
available_at_policy = next_month
rebalance_frequency = monthly
```

A raw date such as `2024-01-31` is normalized to `datetime = 2024-01-31` and `available_at = 2024-02-01`.

## Validation

The loader checks required raw columns, parseable dates, normalized identity fields, required factor values, and duplicate datetime-symbol rows when contract validation requires uniqueness.

## Boundary

This phase only adds the local loader. It does not add remote data access, signal generation, target weight generation, backtests, runtime changes, ML changes, or v0.2 signal schema changes.

## Verification

```bash
PYTHONPATH=src python3 -m pytest tests/test_oap_loader.py tests/test_oap_factor_contract.py -q
PYTHONPATH=src python3 -m pytest -q
```
