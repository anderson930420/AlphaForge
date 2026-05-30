# Phase 44B: Optional ML Demo Research Validation

Phase 44B connects the existing ML demo pipeline to the custom-signal research-validation protocol.

The default ML demo behavior remains unchanged. Research validation only runs when explicitly requested with `--run-research-validation`.

## Default flow

```text
features + monthly returns
  → forward-return labels
  → supervised ML panel
  → sklearn model
  → predictions
  → prediction diagnostics
  → cross-sectional ml_signal.csv
  → ml_demo_summary.json
```

## Optional research-validation flow

When `--run-research-validation` is enabled:

```text
features + monthly returns
  → forward-return labels
  → supervised ML panel
  → sklearn model
  → predictions
  → prediction diagnostics
  → cross-sectional ml_signal.csv
  → single-symbol projection
  → existing custom_signal research-validation protocol
  → research_protocol_summary.json
  → ml_demo_research_validation_summary.json
  → ml_demo_summary.json
```

## CLI example

```bash
PYTHONPATH=src python3 scripts/run_ml_demo_pipeline.py \
  --features tests/fixtures/ml_demo_pipeline/features.csv \
  --returns tests/fixtures/ml_demo_pipeline/monthly_returns.csv \
  --output-dir artifacts/phase44b/ml_demo_pipeline \
  --model ridge_regressor \
  --feature-cols Mom12m,BM,Investment \
  --label-col ret_fwd_1m \
  --train-end 2024-03-31 \
  --long-quantile 0.8 \
  --short-quantile 0.2 \
  --diagnostic-quantiles 2 \
  --run-research-validation \
  --research-validation-market-data tests/fixtures/ml_signal_research_validation/market_data.csv \
  --research-validation-symbol A \
  --research-validation-development-start 2024-01-31 \
  --research-validation-development-end 2024-03-31 \
  --research-validation-holdout-start 2024-04-30 \
  --research-validation-holdout-end 2024-06-30 \
  --research-validation-train-size 2 \
  --research-validation-test-size 1 \
  --research-validation-step-size 1
```

## Output structure

```text
output_dir/
├── return_labels.csv
├── supervised_panel.csv
├── model/
│   ├── predictions.csv
│   └── metrics.json
├── ml_prediction_diagnostics/
├── signal/
│   └── ml_signal.csv
├── research_validation/
│   ├── derived_signal/
│   │   └── single_symbol_signal.csv
│   ├── ml_signal_single_symbol_validation/
│   │   └── research_protocol_summary.json
│   └── ml_demo_research_validation_summary.json
└── ml_demo_summary.json
```

## Boundary

Phase 44B does not add a new backtest engine. It connects the generated ML signal to the existing one-symbol `custom_signal` research-validation workflow.

It does not:

- add multi-symbol portfolio validation
- change model training
- change prediction generation
- change custom-signal semantics
- change backtest execution semantics
- execute live trades

## Relationship to Phase 44A and Phase 44C

- Phase 44A added a standalone single-symbol projection research-validation script.
- Phase 44C added a clean single-asset threshold converter.
- Phase 44B wires optional research validation into the original ML demo pipeline.

## Testing

```bash
PYTHONPATH=src python3 -m pytest tests/test_ml_demo_pipeline_research_validation.py -q
```
