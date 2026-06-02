# CRSP ML Experiment Comparison

This phase adds a research comparison layer over existing CRSP ML experiment artifacts.

It answers one question:

> Did cross-sectional preprocessing and ML modeling improve over the raw-feature ML baseline and the Mom12m benchmark?

This layer does not train a new model, rebuild a dataset, add live trading, or change the default CRSP sklearn baseline. It only reads previously generated artifacts and turns them into a deterministic comparison report.

## Inputs

ML experiment directories are passed with repeatable `NAME=DIR` arguments. Each directory should normally contain:

```text
<experiment_dir>/
  summary.json
  prediction_portfolio_returns.parquet   optional
  window_metrics.json                    optional
```

The minimum required file is `summary.json`.

The optional Mom12m benchmark directory should contain:

```text
<mom12m_dir>/
  momentum_summary.json
  momentum_portfolio_returns.parquet     optional
```

## Outputs

The CLI writes:

```text
<output_dir>/
  comparison.json
  comparison.md
```

The JSON artifact includes:

- report type and metadata
- loaded ML experiment records
- optional Mom12m benchmark record
- ranking summary
- deterministic research interpretation
- limitations
- next steps
- generated output paths

## CLI

```bash
PYTHONPATH=src python3 scripts/build_crsp_ml_experiment_comparison.py \
  --experiment raw_ridge=artifacts/crsp_ml_e2e/sklearn_baseline \
  --experiment xrank_ridge=artifacts/crsp_sklearn_baseline_xrank \
  --mom12m-dir artifacts/crsp_mom12m_baseline \
  --output-dir artifacts/crsp_ml_experiment_comparison
```

`--mom12m-dir` is optional. If it is omitted, the report still compares ML experiments and leaves the benchmark section empty.

## Interpretation Logic

The interpretation is deterministic and based only on loaded artifact values.

Rules include:

- If cross-sectional rank or xrank preprocessing improves average prediction Rank IC relative to raw features, the report states that ranking quality improved directionally.
- If the best ML cumulative return is below Mom12m, the report states that ML did not outperform the benchmark over the observed comparison window.
- If Rank IC remains small, negative, unavailable, or portfolio returns remain weak, the report states that the evidence is not enough to claim robust alpha.
- The report recommends transaction costs, target clipping, feature neutralization, hyperparameter tuning, and richer fundamentals as next steps.

## How This Supports Interview Presentation

This phase turns the real-data CRSP work into a research conclusion instead of a loose collection of pipeline artifacts.

The intended interview narrative is:

1. Build a clean external CRSP monthly panel adapter.
2. Construct a non-ML Mom12m benchmark.
3. Build supervised ML datasets and chronological walk-forward splits.
4. Train sklearn baselines and produce prediction-ranked portfolios.
5. Apply cross-sectional preprocessing such as rank normalization.
6. Compare raw ML, transformed-feature ML, and Mom12m in one artifact-backed report.
7. Explain what improved, what did not, and what should be tested next.

The important claim is process quality, not guaranteed profitability.

## Current Limitations

- No transaction costs
- No hyperparameter tuning
- No industry neutralization
- No feature neutralization
- No target clipping
- No Compustat fundamentals
- No live trading or broker integration
- Report-only layer; it does not rerun experiments

## Next Research Steps

- Add transaction-cost and turnover-aware diagnostics.
- Add target clipping or winsorized labels.
- Add hyperparameter tuning inside the walk-forward process.
- Add sector or industry neutralization.
- Add richer point-in-time fundamentals when available.
- Compare additional preprocessing variants such as z-score and winsorized z-score.
