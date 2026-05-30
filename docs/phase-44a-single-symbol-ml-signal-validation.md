# Phase 44A: Single-Symbol ML Signal Research Validation

Phase 44A closes the first ML research-validation loop without adding a multi-symbol portfolio engine.

It projects an already-generated cross-sectional AlphaForge ML signal to one selected symbol, runs preflight health checks, writes a derived single-symbol `custom_signal` file, and validates it through the existing `custom_signal` research-validation protocol.

## Pipeline flow

```text
multi-symbol ml_signal.csv
  → select signal_name, if needed
  → project to one symbol
  → derived_signal/single_symbol_signal.csv
  → signal / market datetime alignment preflight
  → existing custom_signal research-validate workflow
  → ml_signal_research_validation_summary.json
```

## Why this exists

The Phase 33 ML demo pipeline stops at `signal/ml_signal.csv`. That artifact is a multi-symbol, cross-sectional ML signal. AlphaForge's current `custom_signal` runtime validation is intentionally one-symbol, so the multi-symbol signal cannot be passed directly into `research-validate`.

Phase 44A therefore adds a thin bridge:

```text
cross-sectional ML signal → single-symbol projection → existing research validation
```

It does not implement portfolio-level cross-sectional backtesting.

## CLI usage

```bash
PYTHONPATH=src python3 scripts/run_ml_signal_research_validation.py \
  --signal-file artifacts/phase33/ml_demo_pipeline/signal/ml_signal.csv \
  --market-data tests/fixtures/ml_signal_research_validation/market_data.csv \
  --symbol A \
  --signal-name ml_predicted_return \
  --output-dir artifacts/phase44/ml_signal_research_validation \
  --experiment-name ml_signal_single_symbol_validation \
  --development-start 2024-01-31 \
  --development-end 2024-03-31 \
  --holdout-start 2024-04-30 \
  --holdout-end 2024-06-30 \
  --train-size 2 \
  --test-size 1 \
  --step-size 1
```

## Output structure

```text
artifacts/phase44/ml_signal_research_validation/
├── input_summary.json
├── derived_signal/
│   └── single_symbol_signal.csv
├── ml_signal_single_symbol_validation/
│   └── research_protocol_summary.json
└── ml_signal_research_validation_summary.json
```

The exact nested research-validation artifacts are owned by the existing `custom_signal` research-validation workflow.

## Health checks

### 1. Nonzero exposure check

The script records:

```json
"nonzero_target_weight_count": 6,
"all_flat_selected_symbol": false
```

If the selected symbol has zero nonzero `target_weight` rows, the script emits a warning but does not fail. An all-flat strategy is valid, but it is usually a poor demo artifact.

### 2. Signal / market date alignment

The script checks that selected signal dates are a subset of market-data dates before invoking research validation.

This catches the common month-end fixture problem where ML signals are month-end dated but the market-data CSV does not contain those exact dates.

## Boundaries

Phase 44A explicitly does not:

- train a model
- generate predictions
- add multi-symbol portfolio backtesting
- execute live trades
- change the `custom_signal` runtime contract
- change backtest execution semantics

It only bridges an existing ML signal artifact into the existing one-symbol `custom_signal` research-validation workflow.

## Testing

```bash
PYTHONPATH=src python3 -m pytest tests/test_run_ml_signal_research_validation.py -q
```

The test suite covers:

- successful projection and research validation
- missing selected symbol fail-fast
- signal/market date mismatch fail-fast
- all-flat selected symbol warning without failure
- multiple `signal_name` values requiring explicit `--signal-name`
