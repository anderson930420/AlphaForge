# Phase 44C: Single-Asset ML Signal Converter

Phase 44C adds a clean single-asset ML signal story:

```text
single-asset predictions.csv
  → time-series threshold converter
  → one-symbol custom_signal v0.2 CSV
```

This is different from Phase 44A. Phase 44A projects a cross-sectional ML signal to one symbol and validates it through `custom_signal` research validation. Phase 44C directly converts one asset's prediction time series into a one-symbol signal.

## Signal rule

The converter uses fixed prediction thresholds:

```text
predicted_return > long_threshold   → direction = 1,  target_weight = long_target_weight
predicted_return < short_threshold  → direction = -1, target_weight = short_target_weight
otherwise                           → direction = 0,  target_weight = 0.0
```

By default:

```text
long_threshold = 0.0
short_threshold = 0.0
long_target_weight = 1.0
short_target_weight = -1.0
```

## CLI usage

```bash
PYTHONPATH=src python3 scripts/run_single_asset_ml_signal.py \
  --predictions tests/fixtures/single_asset_ml_signal/predictions.csv \
  --output artifacts/phase44c/single_asset_signal/signal.csv \
  --summary-output artifacts/phase44c/single_asset_signal/summary.json \
  --asset-id A \
  --long-threshold 0.01 \
  --short-threshold -0.01
```

## Output signal schema

The output is an AlphaForge v0.2 custom signal:

```text
datetime,available_at,symbol,asset_id,signal_name,score,direction,target_weight,source
```

## Why this exists

The cross-sectional ML signal converter needs at least two useful scores per date; a one-asset panel can become all neutral under quantile selection. Phase 44C adds a time-series threshold converter so a single asset can produce a meaningful long / short / flat signal without depending on cross-sectional dispersion.

## Boundaries

Phase 44C does not:

- train a model
- generate predictions
- run research validation
- add multi-symbol portfolio backtesting
- change backtest execution semantics

It only converts existing predictions into a one-symbol custom signal.

## Testing

```bash
PYTHONPATH=src python3 -m pytest tests/test_single_asset_ml_signal.py -q
```
