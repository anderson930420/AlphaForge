# CRSP ML Cross-Sectional Preprocessing

This PR adds a deterministic preprocessing layer that transforms the existing
CRSP ML dataset month by month before model training.

It is designed for research workflows where raw monthly features are useful as
inputs, but downstream models benefit from cross-sectional normalization.

## Why This Exists

Raw CRSP features often have different scales, skew, and month-to-month regime
shifts. A model that trains on the raw panel can end up learning absolute
levels instead of relative position within each month.

This layer converts each month independently so the transformed features are
only based on contemporaneous asset values from the same date.

## Supported Methods

- `rank`
  - percentile rank within each month
  - transformed value is `percentile_rank - 0.5`
  - percentile rank is shifted by `-0.5`, not a strict zero-mean transform
- `zscore`
  - month-by-month z-score across assets
- `winsorized_zscore`
  - winsorize within the month first
  - then z-score the clipped values

## No-Lookahead Rules

- Transformations are computed within each month only.
- No future months are used in any transformation.
- The label column is not used for preprocessing.
- The raw label column remains unchanged in the output dataset.

## Artifact Layout

- Preprocessed dataset parquet
- QC JSON
- Feature columns JSON

The feature columns manifest is a canonical CRSP ML feature-selection payload
with preprocessing metadata such as:

```json
{
  "feature_columns": ["mom12_1_xrank", "mom6_1_xrank"],
  "count": 2,
  "raw_feature_columns": ["mom12_1", "mom6_1"],
  "method": "rank",
  "label_column": "forward_1m_total_ret",
  "date_column": "date",
  "asset_column": "asset_id",
  "keep_original_features": true,
  "lower_quantile": null,
  "upper_quantile": null
}
```

## CLI

```bash
PYTHONPATH=src python3 scripts/build_crsp_ml_preprocessed_dataset.py \
  --input artifacts/crsp_ml_e2e/dataset/crsp_ml_dataset.parquet \
  --output artifacts/crsp_ml_preprocessed_dataset/crsp_ml_dataset_xrank.parquet \
  --qc-output artifacts/crsp_ml_preprocessed_dataset/crsp_ml_dataset_xrank_qc.json \
  --feature-columns-output artifacts/crsp_ml_preprocessed_dataset/feature_columns_xrank.json \
  --method rank \
  --drop-missing-label \
  --keep-original-features
```

## Using The Feature Columns With Sklearn

The sklearn baseline CLI now accepts `--feature-columns-json`. That lets the
baseline train on the transformed feature set without hard-coding the list in
the command line.

```bash
PYTHONPATH=src python3 scripts/run_crsp_sklearn_baseline.py \
  --splits-dir artifacts/crsp_ml_walkforward_xrank \
  --output-dir artifacts/crsp_sklearn_baseline_xrank \
  --model ridge \
  --quantile 0.1 \
  --random-state 0 \
  --feature-columns-json artifacts/crsp_ml_preprocessed_dataset/feature_columns_xrank.json
```

## Current Limitations

- No industry neutralization
- No sector controls
- No transaction costs
- No model hyperparameter tuning
- No Compustat fundamentals
- No target clipping in this PR

## Boundary Notes

- No torch/deep learning
- No dashboard integration
- No changes to the default CRSP ML dataset builder
- No changes to walk-forward split logic
- No raw CRSP data committed to the repository
