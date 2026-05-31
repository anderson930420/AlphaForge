# Phase 60: Classifier Signal Research-Validation Demo

Phase 60 closes the classifier path through AlphaForge's existing single-symbol `custom_signal` research-validation protocol.

## Purpose

Previous phases added:

```text
classifier baseline → predicted_probability artifacts
classifier probability → v0.2 custom_signal conversion
```

This phase adds a demo script that runs:

```text
classifier predictions.csv
  → classifier probability signal
  → single-symbol projection
  → custom_signal research validation
  → final holdout artifacts
  → Streamlit-showcase-compatible artifact layout
```

## Script

```bash
PYTHONPATH=src python3 scripts/run_classifier_signal_research_validation_demo.py \
  --predictions tests/fixtures/classifier_signal_research_validation/predictions.csv \
  --market-data tests/fixtures/ml_signal_research_validation/market_data.csv \
  --symbol C \
  --output-dir artifacts/demo/classifier_signal_demo_C \
  --development-start 2024-01-31 \
  --development-end 2024-03-31 \
  --holdout-start 2024-04-30 \
  --holdout-end 2024-06-30 \
  --train-size 2 \
  --test-size 1 \
  --step-size 1
```

## Output layout

The output intentionally matches the interview Streamlit showcase convention:

```text
ml_demo_summary.json
model/predictions.csv
signal/ml_signal.csv
research_validation/ml_demo_research_validation_summary.json
research_validation/derived_signal/single_symbol_signal.csv
research_validation/ml_signal_single_symbol_validation/final_holdout/metrics_summary.json
research_validation/ml_signal_single_symbol_validation/final_holdout/equity_curve.csv
research_validation/ml_signal_single_symbol_validation/final_holdout/trade_log.csv
```

This means the Streamlit showcase can open this run directory directly.

## Demo health checks

The summary records:

```text
nonzero_target_weight_count
all_flat_selected_symbol
extra_signal_dates
warnings
```

For interview demos, choose a symbol where:

```text
nonzero_target_weight_count > 0
extra_signal_dates == []
warnings == []
```

## Boundary

This phase does not:

- train a classifier
- choose optimal thresholds
- add multi-symbol portfolio validation
- perform live trading
- claim profitable alpha from fixture data

It consumes existing classifier predictions and reuses the existing one-symbol `custom_signal` validation path.

## Testing

```bash
PYTHONPATH=src python3 -m pytest tests/test_classifier_signal_research_validation_demo.py -q
```
