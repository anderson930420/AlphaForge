# Phase 28 — Single-Factor Diagnostics

## Goal

Phase 28 adds a model-free research diagnostics layer for evaluating a single
asset-pricing factor before converting it into a strategy or ML feature.

The goal is to answer:

```text
Does this factor have cross-sectional signal quality against future returns?
```

This phase does not train a model, run a backtest, or modify `custom_signal`
semantics. It evaluates factor quality from a supervised feature-label panel.

## Inputs

A supervised panel with at least:

```text
asset_id, date, <factor column>, ret_fwd_1m
```

Tiny fixture smoke example:

```bash
PYTHONPATH=src python3 scripts/run_factor_diagnostics.py \
  --panel artifacts/phase25/ml_artifact_smoke/supervised_panel.csv \
  --output-dir artifacts/phase28/mom12m_diagnostics \
  --factor-col Mom12m \
  --label-col ret_fwd_1m \
  --quantiles 2
```

Use higher quantile counts such as `--quantiles 5` only when each date has a
large enough cross section. The checked-in ML smoke fixture is intentionally tiny
and has at most two assets per date, so five-quantile buckets are skipped.

## Outputs

The script writes:

```text
factor_summary.json
factor_coverage_by_date.csv
factor_distribution_by_date.csv
factor_ic_timeseries.csv
factor_quantile_returns.csv
factor_long_short_spread.csv
```

## Diagnostics

### Coverage

Per-date factor availability:

```text
date, asset_count, valid_factor_count, missing_factor_count, coverage_ratio
```

### Distribution

Per-date factor distribution:

```text
date, count, mean, std, min, median, max
```

### IC and Rank IC

Per-date cross-sectional correlation between the factor and future return:

```text
IC      = corr(factor_value, ret_fwd_1m)
Rank IC = corr(rank(factor_value), rank(ret_fwd_1m))
```

Thin or constant cross sections produce null IC values instead of misleading
numbers.

### Quantile returns

Per-date quantile bucket forward returns:

```text
date, quantile, quantile_number, asset_count, mean_forward_return, median_forward_return
```

Thin dates where the valid cross section is smaller than the requested quantile
count are skipped instead of forcing unstable buckets.

### Long-short spread

Top quantile minus bottom quantile mean forward return:

```text
long_short_spread = mean_forward_return(QN) - mean_forward_return(Q1)
```

where `N` is the selected number of quantiles.

## Boundary

This phase does not:

- train ML or deep learning models
- run portfolio optimization
- run backtests
- modify signal construction
- modify the dashboard
- download private OAP/CRSP/WRDS data

Dashboard integration is intentionally deferred to a later phase.

## Validation

Recommended checks:

```bash
git diff --check
PYTHONPATH=src python3 -m pytest tests/test_factor_diagnostics.py -q
PYTHONPATH=src python3 -m pytest -q
```
