# CRSP Mom12m Baseline

This is AlphaForge’s first real-data CRSP monthly baseline. It uses an external
monthly parquet panel generated outside the repository and computes the classic
`mom12_1` signal, defined as cumulative total return from `t-12` through `t-2`
while skipping `t-1`.

The baseline is intentionally non-ML. It exists as a benchmark for future
research workflows and to validate the external CRSP monthly panel adapter.

## What It Does

- Loads the external CRSP monthly parquet with `load_crsp_monthly_panel`
- Computes `mom12_1` from `total_ret`
- Derives `forward_1m_total_ret` as the next-month `total_ret` by `asset_id`
- Builds a top-minus-bottom quantile long-short portfolio
- Writes signal, portfolio return, and summary artifacts

## Boundary Notes

- Raw CRSP data is not committed to the repo.
- Generated artifacts are local-only and can be recreated from the external
  parquet at any time.
- The implementation does not introduce ML logic, dashboard changes, or OAP
  behavior changes.
- The script loads the full monthly history so the initial analysis window still
  has enough lookback to compute momentum correctly.

## CLI

```bash
PYTHONPATH=src python3 scripts/run_crsp_mom12m_baseline.py \
  --input "/Users/anderson930420/Desktop/crsp_parquet/monthly/crsp_monthly_1995_2023.parquet" \
  --output-dir artifacts/crsp_mom12m_baseline \
  --start-date 1996-01-31 \
  --end-date 2023-12-31 \
  --quantile 0.1 \
  --min-obs 8 \
  --weighting equal \
  --common-shares-only \
  --primary-exchange-only
```

## Outputs

- `momentum_signal_panel.parquet`
- `momentum_portfolio_returns.parquet`
- `momentum_summary.json`

The JSON summary includes the date range, return statistics, and the output
paths for the generated artifacts.
