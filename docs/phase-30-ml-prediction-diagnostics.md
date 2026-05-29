# Phase 30 — ML Prediction Diagnostics

## Goal

Phase 30 evaluates ML predictions as a cross-sectional signal.

This phase answers:

```text
Do predicted returns rank future returns well enough to be useful as a signal?
```

It does not train models, build a dashboard view, run a backtest, or modify signal construction.

## Input

A predictions artifact with at least:

```text
asset_id, date, predicted_return, ret_fwd_1m
```

Example:

```bash
PYTHONPATH=src python3 scripts/run_ml_prediction_diagnostics.py \
  --predictions artifacts/phase25/ml_artifact_smoke/predictions.csv \
  --output-dir artifacts/phase30/ml_prediction_diagnostics_q2 \
  --prediction-col predicted_return \
  --label-col ret_fwd_1m \
  --quantiles 2
```

Use higher quantile counts such as `--quantiles 5` only when each date has a large enough cross section.

## Outputs

```text
ml_prediction_summary.json
ml_prediction_ic_timeseries.csv
ml_prediction_quantile_returns.csv
ml_prediction_long_short_spread.csv
ml_prediction_error_by_date.csv
```

## Diagnostics

- Prediction IC: correlation between predicted return and future return by date
- Prediction Rank IC: rank correlation between predicted return and future return by date
- Prediction quantile returns: realized forward returns by prediction bucket
- Prediction long-short spread: top prediction bucket minus bottom prediction bucket
- Error by date: MSE, MAE, mean error, mean prediction, and mean label

## Boundary

This phase evaluates existing predictions. It does not recompute predictions, train models, run backtests, update the dashboard, or change custom_signal semantics.

## Validation

```bash
git diff --check
PYTHONPATH=src python3 -m pytest tests/test_ml_diagnostics.py -q
PYTHONPATH=src python3 -m pytest -q
```
