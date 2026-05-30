# Phase 45A: Sklearn Classifier Baseline

Phase 45A adds the first classification layer to AlphaForge ML.

It builds binary forward-return labels and trains sklearn classifiers that output predicted probabilities. This is separate from the existing regression baseline path.

## Label rule

The binary target is:

```text
forward_return > threshold → 1
forward_return <= threshold → 0
```

Default settings:

```text
return_col = ret_fwd_1m
label_col = ret_fwd_1m_positive
threshold = 0.0
```

## Supported classifiers

```text
logistic_regression_classifier
random_forest_classifier
hist_gradient_boosting_classifier
```

## CLI usage

```bash
PYTHONPATH=src python3 scripts/run_sklearn_classifier_baseline.py \
  --features tests/fixtures/ml_demo_pipeline/features.csv \
  --returns tests/fixtures/ml_demo_pipeline/monthly_returns.csv \
  --output-dir artifacts/phase45a/classifier_baseline \
  --classifier logistic_regression_classifier \
  --feature-cols Mom12m,BM,Investment \
  --return-label-col ret_fwd_1m \
  --classification-label-col ret_fwd_1m_positive \
  --classification-threshold 0.0 \
  --train-end 2024-03-31
```

## Output structure

```text
artifacts/phase45a/classifier_baseline/
├── return_labels.csv
├── classification_labels.csv
├── supervised_classifier_panel.csv
├── classifier/
│   ├── predictions.csv
│   ├── metrics.json
│   ├── feature_importance.csv
│   └── train_config.json
└── classifier_baseline_summary.json
```

## Prediction artifact

`classifier/predictions.csv` includes:

```text
asset_id
date
predicted_probability
predicted_class
classifier_name
positive_class
ret_fwd_1m_positive
```

## Metrics artifact

`classifier/metrics.json` includes:

```text
accuracy
precision
recall
roc_auc
positive_rate
prediction_positive_rate
mean_predicted_probability
train_row_count
test_row_count
classes
positive_class
```

`roc_auc` is emitted as `null` when the evaluation slice has only one observed class.

## Boundary

Phase 45A does not:

- convert predicted probabilities into trading signals
- run custom-signal research validation
- add torch classifiers
- add multi-symbol portfolio validation
- execute live trades

It only creates binary labels and sklearn classifier artifacts.

## Testing

```bash
PYTHONPATH=src python3 -m pytest \
  tests/test_classification_labels.py \
  tests/test_ml_classifiers.py \
  tests/test_run_sklearn_classifier_baseline.py \
  -q
```
