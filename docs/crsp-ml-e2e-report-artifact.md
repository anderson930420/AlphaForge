# CRSP ML E2E Report Artifact

This artifact is a presentation layer over the existing CRSP ML end-to-end outputs. It does not rerun the pipeline, retrain any model, or change the dataset, walk-forward, or sklearn baseline behavior.

## What It Reads

The report builder reads the existing E2E artifact root and expects these files:

```text
<e2e_dir>/
  e2e_summary.json
  dataset/
    crsp_ml_dataset_qc.json
  walkforward/
    walk_forward_qc.json
  sklearn_baseline/
    summary.json
    window_metrics.json
    prediction_portfolio_returns.parquet
```

The parquet file is optional. When present, the report includes a compact monthly cumulative-return preview.

## What It Writes

The report builder writes a separate report directory:

```text
<output_dir>/
  report.json
  report.md
  report.html
```

Use `--no-html` to skip `report.html`.

## CLI

```bash
PYTHONPATH=src python3 scripts/build_crsp_ml_e2e_report.py \
  --e2e-dir artifacts/crsp_ml_e2e \
  --output-dir artifacts/crsp_ml_e2e/report
```

## Report Content

The report summarizes:

- pipeline context
- dataset QC
- walk-forward split QC
- sklearn baseline metrics
- portfolio performance summary
- window-level diagnostics
- artifact paths for the input bundle and generated report files

## Limitations

- No transaction costs are modeled.
- No hyperparameter tuning is performed.
- No feature neutralization is applied.
- No cross-sectional preprocessing is added.
- No Compustat features are introduced.
- No torch or deep learning is used.
- No dashboard integration is added.
- The report is generated from existing artifacts only.
