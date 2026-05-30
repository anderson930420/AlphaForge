# Phase 47A: ML Model Comparison Report

Phase 47A adds a lightweight comparison report for existing AlphaForge ML demo runs.

It is an artifact aggregator, not a model runner. It reads completed run directories and produces a comparable table across models.

## Inputs

Each run directory must contain:

```text
ml_demo_summary.json
model/metrics.json
ml_prediction_diagnostics/ml_prediction_summary.json
```

If available, the report also reads:

```text
research_validation/ml_demo_research_validation_summary.json
```

## CLI usage

```bash
PYTHONPATH=src python3 scripts/build_ml_model_comparison_report.py \
  --run ridge_regressor=artifacts/runs/ridge \
  --run random_forest_regressor=artifacts/runs/random_forest \
  --output-dir artifacts/model_comparison \
  --sort-by overall_mae
```

## Outputs

```text
artifacts/model_comparison/
├── model_comparison.csv
└── model_comparison_summary.json
```

## Compared fields

The comparison CSV includes prediction-side metrics:

- MSE / MAE
- prediction-label correlation
- prediction IC / Rank-IC
- long-short spread mean
- row counts and feature columns

If optional Phase 44B research-validation artifacts exist, it also includes holdout-side metrics:

- final holdout total return
- annualized return
- Sharpe ratio
- max drawdown
- turnover
- trade count

## Ranking

Default ranking uses:

```text
overall_mae ascending lower-is-better
```

Supported `--sort-by` values:

```text
overall_mae
overall_mse
prediction_rank_ic_mean
prediction_ic_mean
long_short_spread_mean
holdout_total_return
holdout_sharpe_ratio
```

Error metrics rank ascending. Signal / performance metrics rank descending.

## Boundary

Phase 47A does not:

- train models
- generate predictions
- run backtests
- run research validation
- change model behavior
- change strategy execution semantics
- execute live trades

It only aggregates existing artifacts into a comparison table and summary JSON.

## Testing

```bash
PYTHONPATH=src python3 -m pytest tests/test_ml_model_comparison_report.py -q
```
