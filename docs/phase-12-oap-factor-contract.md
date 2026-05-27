# Phase 12 OAP Factor Contract

## Summary

Phase 12 adds a minimal deterministic OAP / JKP factor data contract layer for AlphaForge.

This phase freezes the first machine-readable contract shape for converting Open Asset Pricing / JKP-style characteristics into the existing AlphaForge v0.2 signal path in later phases.

## What changed

- Added `alphaforge.oap_factor_contract`.
- Added `OAPFactorContract` and `OAPFactorContractError`.
- Added `load_oap_factor_contract(...)`.
- Added `validate_oap_factor_contract(...)`.
- Added a valid Mom12m threshold-rule fixture:
  - `tests/fixtures/oap_factor_contracts/mom12m_threshold.yaml`
- Added contract validation tests.

## Supported contract version

```text
alphaforge_oap_factor_contract_v0.1
```

## Required sections

```text
dataset
factor
decision_rule
weighting
timing
identity
validation
output
```

## First supported decision rule

Phase 12 supports only threshold rules:

```yaml
decision_rule:
  type: threshold
  long_threshold: 0.0
  short_threshold: 0.0
  long_when: greater_than
  short_when: less_than
```

This is intended for Mom12m-style factors where positive values can map to long exposure and negative values can map to short exposure.

## First supported weighting mode

Phase 12 supports only signed unit weighting:

```yaml
weighting:
  target_weight_mode: signed_unit
  long_weight: 1.0
  short_weight: -1.0
  neutral_weight: 0.0
```

Validation requires:

```text
0 < long_weight <= 1
-1 <= short_weight < 0
neutral_weight == 0
```

## First supported timing policy

Phase 12 supports only monthly next-month availability:

```yaml
timing:
  datetime_col: date
  available_at_policy: next_month
  rebalance_frequency: monthly
```

The actual `available_at` materialization is intentionally left to the later OAP loader phase.

## Output schema

Phase 12 keeps the existing AlphaForge v0.2 signal schema:

```yaml
output:
  schema: signal_csv_v0.2
```

This phase does not change `signal.csv` columns.

## Boundary

This phase only adds the contract layer.

It intentionally does **not**:

- download real OAP / JKP data
- add an OAP loader
- add cross-sectional ranking rules
- run AlphaForge backtests
- change AlphaForge runtime semantics
- change SignalForge package format
- change ML behavior
- change `signal.csv` v0.2 schema

## Verification

```bash
PYTHONPATH=src python3 -m pytest tests/test_oap_factor_contract.py -q
PYTHONPATH=src python3 -m pytest -q
```

## Next phase

The next phase should be OAP loader work:

```text
Phase 13 — oap-loader
```

That phase should read real OAP / JKP files, normalize columns, generate `available_at` from `available_at_policy`, and produce a normalized factor frame based on this contract.
