# CRSP ML Walk-Forward Split Layer

This PR adds a deterministic walk-forward split layer on top of the existing
CRSP ML dataset baseline.

It does **not** train a model. It only slices an existing CRSP ML parquet into
time-ordered train/test windows and writes split artifacts plus QC metadata.

## Why This Exists

Random train/test splits are a poor fit for asset-pricing and return-prediction
workflows because they can leak future regime information backward in time. A
model evaluated with random row-level shuffling can look better than it really
is because the train set may contain later months from the same assets.

This layer keeps the evaluation chronology intact by using fixed-length rolling
walk-forward windows.

## Window Design

The split generator uses:

- `train_years`: trailing history in each training window
- `test_years`: forward holdout length per window
- `step_years`: how far the window advances each iteration

For the default `10/1/1` configuration, the first window is:

- train: 10 years
- test: 1 year
- step: 1 year

All boundaries are month-end aware, and the final partial window is excluded.

## Artifact Layout

Each window is written to its own directory:

- `<output-dir>/<window_id>/train.parquet`
- `<output-dir>/<window_id>/test.parquet`

The CLI also writes:

- QC JSON
- optional manifest JSON

## CLI

```bash
PYTHONPATH=src python3 scripts/build_crsp_ml_walk_forward_splits.py \
  --input artifacts/crsp_ml_dataset/crsp_ml_dataset_1996_2023.parquet \
  --output-dir artifacts/crsp_ml_walkforward \
  --start-date 1996-01-31 \
  --end-date 2023-11-30 \
  --train-years 10 \
  --test-years 1 \
  --step-years 1 \
  --qc-output artifacts/crsp_ml_walkforward/walk_forward_qc.json \
  --manifest-output artifacts/crsp_ml_walkforward/walk_forward_manifest.json
```

## Current Limitations

- No model training
- No sklearn integration
- No torch integration
- No feature scaling
- No cross-sectional ranking
- No hyperparameter tuning
- No dashboard changes

## Notes

- Raw CRSP data is not committed to the repository.
- The external CRSP parquet path is only used at runtime by the CLI.
- The split layer reuses the existing CRSP ML dataset and does not change how
  that dataset is built.
