# CRSP ML E2E Pipeline

This pipeline stitches together the existing CRSP monthly panel loader, ML dataset builder, walk-forward splitter, and optional sklearn baseline into one reproducible command.

## Boundaries

- Uses the external canonical CRSP monthly parquet as input.
- Reuses the existing dataset builder and walk-forward splitter.
- Reuses the existing sklearn baseline models only.
- Does not add new model types, torch, dashboard code, or CRSP data fixtures.
- Does not hard-code any local data path in library code.

## Artifact Layout

```text
<output_dir>/
  dataset/
    crsp_ml_dataset.parquet
    crsp_ml_dataset_qc.json
  walkforward/
    <window_id>/
      train.parquet
      test.parquet
    walk_forward_qc.json
    walk_forward_manifest.json
  sklearn_baseline/
    predictions.parquet
    window_metrics.json
    prediction_portfolio_returns.parquet
    summary.json
  e2e_summary.json
```

## CLI

```bash
PYTHONPATH=src python3 scripts/run_crsp_ml_e2e_pipeline.py \
  --monthly-input "/Users/anderson930420/Desktop/crsp_parquet/monthly/crsp_monthly_1995_2023.parquet" \
  --output-dir artifacts/crsp_ml_e2e \
  --start-date 1996-01-31 \
  --end-date 2023-12-31 \
  --min-mom-obs 8 \
  --drop-missing-label \
  --common-shares-only \
  --primary-exchange-only \
  --train-years 10 \
  --test-years 1 \
  --step-years 1 \
  --model ridge \
  --quantile 0.1 \
  --random-state 0
```

## Notes

- The final dataset date range may end one month before `--end-date` because the last month is dropped when the forward-return label is missing.
- The pipeline prints the final `e2e_summary.json` payload to stdout and writes all artifacts to disk.
- If scikit-learn is unavailable, the pipeline fails with the existing CRSP sklearn baseline dependency message.
