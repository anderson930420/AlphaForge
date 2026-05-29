# Phase 33: ML Demo Pipeline

End-to-end local ML demo pipeline that runs from feature/return files to model predictions, ML diagnostics, and custom_signal artifacts.

## Pipeline flow

```
features.csv + monthly_returns.csv
  → return_labels.csv
  → supervised_panel.csv
  → sklearn regression model (train / predict)
  → model/predictions.csv
  → ml_prediction_diagnostics/
  → signal/ml_signal.csv
  → ml_demo_summary.json
```

## Boundaries

- **No private data**: Uses small deterministic fixtures only. Does not commit OAP/JKP/WRDS/CRSP data.
- **No profitability claim**: This is artifact generation, not strategy validation.
- **No live trading**: Research demo only.
- **No full backtest**: Does not invoke research-validate or walk-forward evaluation.

## Dependencies

Requires scikit-learn:

```bash
python3 -m pip install -e ".[sklearn]"
```

## CLI usage

```bash
PYTHONPATH=src python3 scripts/run_ml_demo_pipeline.py \
  --features tests/fixtures/ml_demo_pipeline/features.csv \
  --returns tests/fixtures/ml_demo_pipeline/monthly_returns.csv \
  --output-dir artifacts/phase33/ml_demo_pipeline \
  --model ridge_regressor \
  --feature-cols Mom12m,BM,Investment \
  --label-col ret_fwd_1m \
  --train-end 2024-03-31 \
  --long-quantile 0.8 \
  --short-quantile 0.2 \
  --diagnostic-quantiles 2
```

## Input format

### features.csv

| asset_id | date       | Mom12m | BM   | Investment |
|----------|------------|--------|------|------------|
| A        | 2024-01-31 | 0.10   | 0.50 | 1000       |

### monthly_returns.csv

| asset_id | date       | ret   |
|----------|------------|-------|
| A        | 2024-01-31 | 0.02  |

## Output structure

```
artifacts/phase33/ml_demo_pipeline/
├── return_labels.csv
├── supervised_panel.csv
├── model/
│   ├── train_config.json
│   ├── model_summary.json
│   ├── predictions.csv
│   ├── metrics.json
│   └── feature_importance.csv
├── ml_prediction_diagnostics/
│   ├── ml_prediction_summary.json
│   ├── ml_prediction_ic_timeseries.csv
│   ├── ml_prediction_quantile_returns.csv
│   ├── ml_prediction_long_short_spread.csv
│   └── ml_prediction_error_by_date.csv
├── signal/
│   └── ml_signal.csv
└── ml_demo_summary.json
```

## Testing

```bash
PYTHONPATH=src python3 -m pytest tests/test_run_ml_demo_pipeline.py -q
```

## Existing modules reused

- `return_labels.py` — forward return label construction and feature-label join
- `ml_dataset.py` — supervised panel to ML dataset, time train/test split
- `ml_models.py` — sklearn model adapters (ridge, random forest, hist GBM)
- `ml_diagnostics.py` — ML prediction diagnostics (IC, quantile returns, error)
- `ml_signal.py` — prediction-to-custom_signal v0.2 converter

## Next

Phase 33B can add full backtest / research-validate on the ml_signal.csv output.
