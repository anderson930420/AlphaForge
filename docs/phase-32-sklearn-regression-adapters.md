# Phase 32: sklearn Regression Model Adapters

## Goal

Add optional sklearn regression model adapters so AlphaForge can train and compare multiple supervised ML models beyond the current internal ridge-style baseline.

## Supported Models

| Model Name                          | sklearn Class                    | Scaling    |
| ----------------------------------- | -------------------------------- | ---------- |
| `ridge_regressor`                   | `sklearn.linear_model.Ridge`     | Standard   |
| `random_forest_regressor`           | `sklearn.ensemble.RandomForestRegressor` | None |
| `hist_gradient_boosting_regressor`  | `sklearn.ensemble.HistGradientBoostingRegressor` | None |

## Optional Dependency

scikit-learn is an optional dependency. Install with:

```bash
python3 -m pip install -e ".[sklearn]"
```

If scikit-learn is not installed, the code fails gracefully with:

```
scikit-learn is required for sklearn model adapters.
Install with: python3 -m pip install -e ".[sklearn]"
```

scikit-learn is not required for the core package or existing test suite.

## Input Format

The script accepts a supervised feature-label panel CSV with columns for asset identifier, date, features, and label. Same format as the Phase 23 ML Baseline scaffold.

Required columns: `asset_id`, `date`, label column (default `ret_fwd_1m`), and numeric feature columns.

## Example Command

```bash
PYTHONPATH=src python3 scripts/run_sklearn_ml_model.py \
  --panel tests/fixtures/ml_baseline/supervised_panel.csv \
  --output-dir artifacts/phase32/sklearn_ridge_demo \
  --model ridge_regressor \
  --label-col ret_fwd_1m \
  --train-end 2024-03-31 \
  --feature-cols Mom12m,BM,Investment
```

## CLI Arguments

| Argument         | Required | Default             | Description                                     |
| ---------------- | -------- | ------------------- | ----------------------------------------------- |
| `--panel`        | Yes      |                     | Path to supervised feature-label panel CSV      |
| `--output-dir`   | Yes      |                     | Directory for output artifacts                  |
| `--model`        | Yes      |                     | sklearn model name                              |
| `--train-end`    | Yes      |                     | Date string for time-based train/test split     |
| `--label-col`    | No       | `ret_fwd_1m`       | Name of the label column                        |
| `--feature-cols` | No       | (auto-inferred)     | Comma-separated feature column names            |
| `--asset-id-col` | No       | `asset_id`          | Name of the asset identifier column             |
| `--date-col`     | No       | `date`              | Name of the date column                         |
| `--random-state` | No       | `42`                | Random seed for reproducibility                 |

If `--feature-cols` is omitted, numeric feature columns are auto-inferred while excluding asset identifier, date, label, and metadata columns like `target_date`, `horizon_months`, `source`, and `ret_fwd*` columns.

## Feature Handling

- Explicit `--feature-cols` accepted; inferred otherwise
- Median imputation for missing numeric features
- Standard scaling only for `ridge_regressor`; tree models use raw values
- Time-based train/test split (no random split)

## Output Artifacts

Each run creates five files in the output directory:

| File                       | Description                                          |
| -------------------------- | ---------------------------------------------------- |
| `train_config.json`        | CLI arguments and resolved feature columns           |
| `model_summary.json`       | Model metadata (name, features, row counts)          |
| `predictions.csv`          | Predictions with columns: `asset_id`, `date`, `predicted_return`, label, `model_name` |
| `metrics.json`             | Regression metrics (MSE, MAE, correlation, row counts) |
| `feature_importance.csv`   | Feature importance/coefficients per model            |

### `predictions.csv` Columns

- `asset_id` — asset identifier
- `date` — date
- `predicted_return` — model prediction score
- `ret_fwd_1m` (or configured label column) — realized label
- `model_name` — model identifier

This format is compatible with Phase 30 ML prediction diagnostics.

### `metrics.json` Keys

- `row_count` — number of prediction rows
- `train_row_count` — training set rows
- `test_row_count` — test set rows
- `mse` — mean squared error
- `mae` — mean absolute error
- `mean_prediction` — mean of predicted values
- `mean_label` — mean of realized labels
- `prediction_label_correlation` — correlation between predictions and labels (if computable)

### `feature_importance.csv` Columns

- `feature` — feature name
- `importance` — importance/coefficient value
- `importance_type` — `coefficient` for ridge, `feature_importances_` for tree models
- `model_name` — model identifier

### `model_summary.json` Keys

- `model_name` — model name string
- `model_type` — model name string
- `feature_cols` — list of feature column names
- `label_col` — label column name
- `train_end` — train/test split date
- `train_row_count` — training set rows
- `test_row_count` — test set rows
- `sklearn_required` — always `true`

### `train_config.json` Keys

- `model_name` — model name string
- `label_col` — label column name
- `train_end` — train/test split date
- `feature_cols` — resolved feature columns
- `asset_id_col` — asset identifier column
- `date_col` — date column
- `random_state` — random seed

## Connection to Phase 30 ML Prediction Diagnostics

The `predictions.csv` output from this phase is directly consumable by Phase 30's `run_ml_prediction_diagnostics.py` script:

```bash
PYTHONPATH=src python3 scripts/run_ml_prediction_diagnostics.py \
  --predictions artifacts/phase32/sklearn_ridge_demo/predictions.csv \
  --output-dir artifacts/phase32/sklearn_ridge_demo/ml_prediction_diagnostics \
  --prediction-col predicted_return \
  --label-col ret_fwd_1m \
  --quantiles 2
```

This enables factor-like diagnostics (quantile returns, rank IC, spread, hit rate) on sklearn model predictions.

## Boundaries and Limitations

This phase adds optional sklearn regression model adapters and prediction artifact generation. It does not:

- Claim profitability
- Run live trading
- Optimize strategy parameters
- Download or require private data
- Implement classification models (deferred to Phase 32B)
- Modify core backtest, custom_signal, OAP, or dashboard behavior
