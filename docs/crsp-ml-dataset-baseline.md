# CRSP ML Dataset Baseline

This is AlphaForge’s first CRSP supervised-learning dataset baseline. It uses
the external canonical CRSP monthly parquet panel and converts it into a clean
monthly asset panel with trailing features and a forward return label.

This PR does not train a model. It only builds the dataset foundation that
future ML experiments can consume.

## What It Builds

- Momentum features:
  - `mom12_1`
  - `mom6_1`
  - `mom3_1`
- Current month return feature:
  - `ret1_0`
- Trailing risk feature:
  - `volatility_12m`
- Microstructure / size features:
  - `turnover`
  - `log_market_cap`
  - `log_price`
- Forward label:
  - `forward_1m_total_ret`

## No-Lookahead Design

- Momentum features use only trailing monthly returns.
- `ret1_0` uses the current month only.
- `volatility_12m` is computed from trailing returns only.
- `forward_1m_total_ret` is built from the next month’s `total_ret` for the
  same asset.
- The dataset is sorted by `date` and `asset_id` before it is written.

## Boundaries

- Raw CRSP data is not committed to the repository.
- The user’s external parquet path is not hard-coded in library code.
- This PR does not train sklearn, torch, or classifier models.
- This PR does not change backtest semantics.
- This PR does not change OAP behavior.
- This PR does not add dashboard integration.
- This PR does not add walk-forward or cross-validation logic.

## CLI

```bash
PYTHONPATH=src python3 scripts/build_crsp_ml_dataset.py \
  --input "/Users/anderson930420/Desktop/crsp_parquet/monthly/crsp_monthly_1995_2023.parquet" \
  --output artifacts/crsp_ml_dataset/crsp_ml_dataset_1996_2023.parquet \
  --qc-output artifacts/crsp_ml_dataset/crsp_ml_dataset_qc.json \
  --start-date 1996-01-31 \
  --end-date 2023-12-31 \
  --min-mom-obs 8 \
  --drop-missing-label \
  --common-shares-only \
  --primary-exchange-only
```

## Artifacts

- `crsp_ml_dataset_1996_2023.parquet`
- `crsp_ml_dataset_qc.json`

The QC summary reports row counts, date range, missing ratios for each feature,
duplicate `asset_id/date` rows, and monthly frequency.
