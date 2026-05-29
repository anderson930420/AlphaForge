# Phase 30B — Synthetic Prediction Demo Artifacts

## Goal

Phase 30B adds a deterministic synthetic prediction demo large enough to exercise Phase 30 cross-sectional diagnostics.

The small ML smoke fixture can have only one predicted asset per date, so IC, Rank IC, quantile returns, and long-short spread may be empty. This phase creates a local demo panel with enough assets per date for those diagnostics to be non-empty.

## What it generates

Default shape:

```text
12 months × 20 assets = 240 prediction rows
```

Outputs:

```text
predictions.csv
synthetic_prediction_demo_summary.json
ml_prediction_diagnostics/ml_prediction_summary.json
ml_prediction_diagnostics/ml_prediction_ic_timeseries.csv
ml_prediction_diagnostics/ml_prediction_quantile_returns.csv
ml_prediction_diagnostics/ml_prediction_long_short_spread.csv
ml_prediction_diagnostics/ml_prediction_error_by_date.csv
```

## Usage

```bash
PYTHONPATH=src python3 scripts/run_synthetic_prediction_demo.py \
  --output-dir artifacts/phase30b/synthetic_prediction_demo \
  --months 12 \
  --assets 20 \
  --quantiles 5
```

The generated artifacts are local demo outputs and should remain outside git.

## Boundary

This is a synthetic demonstration artifact generator. It does not train a model, download market data, claim profitability, run a backtest, or modify signal construction.

## Validation

```bash
git diff --check
PYTHONPATH=src python3 -m pytest tests/test_ml_demo_artifacts.py -q
PYTHONPATH=src python3 -m pytest tests/test_ml_diagnostics.py -q
PYTHONPATH=src python3 -m pytest -q
```
