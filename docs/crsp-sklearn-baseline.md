# CRSP Sklearn Baseline

This PR adds the first sklearn-based baseline on top of the existing CRSP ML
walk-forward split artifacts.

It does **not** build new features or change the CRSP dataset construction
pipeline. Instead, it reads the existing walk-forward train/test parquet files,
trains one regression model per window, predicts the corresponding test split,
and evaluates the predictions as both a regression problem and a cross-sectional
long-short portfolio.

## What It Does

- Loads prebuilt walk-forward split directories from `artifacts/crsp_ml_walkforward`
- Trains a separate sklearn regression model for each walk-forward window
- Predicts next-month total returns on each test split
- Writes combined prediction and portfolio artifacts
- Produces per-window metrics plus an overall summary

## Supported Models

- `ridge` default
- `linear`
- `random_forest`

The CLI also accepts `--feature-columns-json`, which lets the baseline consume
the transformed feature manifest written by the cross-sectional preprocessing
step.

`ridge` and `linear` use a train-fitted preprocessing pipeline with:

- median imputation
- standard scaling
- the selected linear regressor

`random_forest` uses median imputation and a deterministic random forest.

## Leakage Controls

- Preprocessing is fit on train rows only
- Test rows are transformed with the train-fitted pipeline
- Training rows with missing labels are dropped before model fitting
- The walk-forward split layer remains chronological and unchanged
- No future test data is used during model fitting

## Portfolio Evaluation

The baseline turns predictions into a monthly long-short portfolio by ranking
assets cross-sectionally on `predicted_return`:

- top quantile: long
- bottom quantile: short
- middle names: ignored

Evaluation includes:

- regression MSE and MAE
- prediction IC
- prediction rank IC
- a deterministic long-short return series
- the same cumulative and annualized summary formulas used by the momentum baseline

## Boundary Notes

- No hyperparameter tuning
- No cross-sectional normalization inside the baseline itself
- Optional feature-column selection is handled by the CLI, not the model code
- No feature neutralization
- No transaction costs
- No dashboard integration
- No torch/deep learning
- No changes to existing CRSP dataset or walk-forward construction
- No raw CRSP data is committed to the repository

## CLI

```bash
PYTHONPATH=src python3 scripts/run_crsp_sklearn_baseline.py \
  --splits-dir artifacts/crsp_ml_walkforward \
  --output-dir artifacts/crsp_sklearn_baseline \
  --model ridge \
  --quantile 0.1 \
  --random-state 0
```

If you preprocessed the dataset with cross-sectional features, pass the
generated manifest directly:

```bash
PYTHONPATH=src python3 scripts/run_crsp_sklearn_baseline.py \
  --splits-dir artifacts/crsp_ml_walkforward_xrank \
  --output-dir artifacts/crsp_sklearn_baseline_xrank \
  --model ridge \
  --quantile 0.1 \
  --random-state 0 \
  --feature-columns-json artifacts/crsp_ml_preprocessed_dataset/feature_columns_xrank.json
```

## Outputs

- `predictions.parquet`
- `window_metrics.json`
- `prediction_portfolio_returns.parquet`
- `summary.json`

The summary JSON includes the model name, walk-forward window count, combined
prediction row count, prediction date range, average per-window regression and
IC metrics, and the deterministic portfolio return summary.
