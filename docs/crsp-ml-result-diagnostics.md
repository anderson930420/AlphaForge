# CRSP ML Result Diagnostics

This diagnostics layer reads existing CRSP ML result artifacts and turns them into a research-oriented comparison report.

It does not:

- rerun the ML pipeline
- change model training
- change CRSP ML dataset construction
- change walk-forward split logic
- add preprocessing
- add new model types
- add dashboard behavior
- commit CRSP data

When Mom12m artifacts are provided, the diagnostics also compare the prediction-ranked ML portfolio against the Mom12m long-short portfolio over the overlapping date range.

## Inputs

Required ML artifacts:

- `artifacts/crsp_ml_e2e/e2e_summary.json`
- `artifacts/crsp_ml_e2e/sklearn_baseline/summary.json`
- `artifacts/crsp_ml_e2e/sklearn_baseline/window_metrics.json`
- `artifacts/crsp_ml_e2e/sklearn_baseline/prediction_portfolio_returns.parquet`

Optional Mom12m artifacts:

- `artifacts/crsp_mom12m_baseline/momentum_summary.json`
- `artifacts/crsp_mom12m_baseline/momentum_portfolio_returns.parquet`

## Outputs

- `artifacts/crsp_ml_result_diagnostics/diagnostics.json`
- `artifacts/crsp_ml_result_diagnostics/diagnostics.md`

## CLI

```bash
PYTHONPATH=src python3 scripts/build_crsp_ml_result_diagnostics.py \
  --ml-e2e-dir artifacts/crsp_ml_e2e \
  --mom12m-dir artifacts/crsp_mom12m_baseline \
  --output-dir artifacts/crsp_ml_result_diagnostics
```

The `--mom12m-dir` flag is optional. If it is omitted, the diagnostics are still generated but no benchmark comparison section is included.

## What The Diagnostics Report

- ML E2E summary fields from the existing pipeline run
- sklearn baseline summary fields from the existing ML baseline artifact
- walk-forward window diagnostics, including mean and median MSE, MAE, IC, and Rank IC
- best and worst windows by IC and Rank IC
- prediction-ranked portfolio return diagnostics, including cumulative return, annualized return, volatility, Sharpe ratio, and max drawdown
- Mom12m comparison metrics when Mom12m artifacts are available
- a deterministic interpretation that is based only on the observed artifact values

## Current Limitations

- No transaction costs
- No hyperparameter tuning
- No cross-sectional preprocessing yet
- No feature neutralization
- No target clipping
- No Compustat fundamentals
- No deep learning
- Simple equal-weight prediction-ranked portfolio construction if applicable
- This layer is presentation-only and does not rerun the ML pipeline

