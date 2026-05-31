# Phase 59: Classifier Probability Signal Conversion

Phase 59 connects classifier probability artifacts to AlphaForge's v0.2 `custom_signal` contract.

## Purpose

Phase 45A added sklearn classifier baselines that output:

```text
predicted_probability
predicted_class
classifier metrics
```

Phase 59 adds the next bridge:

```text
classifier predictions
  → probability thresholds
  → long / short / neutral direction
  → v0.2 custom_signal rows
```

## Semantics

The converter uses threshold-based probability rules:

```text
predicted_probability >= long_probability_threshold  → long
predicted_probability <= short_probability_threshold → short
otherwise                                            → neutral
```

Default thresholds:

```text
long_probability_threshold = 0.6
short_probability_threshold = 0.4
```

Target weights are normalized per side per date:

```text
all long names on a date sum to gross_long_weight
all short names on a date sum to gross_short_weight
neutral names receive 0.0
```

Default gross weights:

```text
gross_long_weight = 1.0
gross_short_weight = -1.0
```

## Script

```bash
PYTHONPATH=src python3 scripts/build_classifier_signal.py \
  --predictions artifacts/phase45a/classifier_baseline/classifier/predictions.csv \
  --output artifacts/phase59/classifier_signal.csv \
  --long-probability-threshold 0.6 \
  --short-probability-threshold 0.4
```

The output is a v0.2 signal file:

```text
datetime, available_at, symbol, asset_id, signal_name, score, direction, target_weight, source
```

## Boundary

This phase only converts classifier probability artifacts to signal artifacts.

It does not:

- train classifiers
- choose optimal thresholds
- run research validation
- execute live trades
- claim profitability

## Testing

```bash
PYTHONPATH=src python3 -m pytest tests/test_classifier_probability_signal.py -q
```
