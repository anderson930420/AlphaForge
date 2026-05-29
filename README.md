# AlphaForge

A Python research framework for asset-pricing signal research, custom signal
backtesting, and ML-ready artifact generation.

AlphaForge is not a live trading system or broker simulator. It is a
deterministic research toolchain: consume features and signals, run backtests
with lagged execution, produce evidence artifacts, and export ML-compatible
datasets and reports.

## Pipeline Overview

```text
Data / Features
  → Signal Construction
  → Forward Return Labels
  → Supervised ML Dataset
  → Single-Factor Diagnostics
  → Baseline ML Predictions
  → custom_signal v0.2 Signal
  → Backtest / Artifact Reports
  → Local Research Dashboard
```

Features (OAP characteristics, external signals) and returns are kept as separate
schemas. Signals carry target positions. Backtests use lagged close-to-close
execution with configurable semantics.

## Current Capabilities

- custom_signal v0.1 (long/flat) and v0.2 (long/short) file consumption
- SignalForge v0.2 package validation and smoke testing
- OAP / Open Source Asset Pricing characteristic processing
- OAP multi-factor signal builder (cross-sectional ranking, YAML configured)
- forward return label builder (month-end aligned, delisting-aware)
- ML dataset builder (feature inference, missing-label drop, date normalization)
- single-factor diagnostics (coverage, distribution, IC, Rank IC, quantile returns)
- baseline ML regressor (closed-form OLS ridge, median imputation, no sklearn)
- sklearn regression model adapters (Ridge, Random Forest, HistGradientBoosting, optional)
- ML prediction to custom_signal v0.2 converter (quantile-based long/short/neutral)
- HTML artifact report renderer (metric cards, Plotly equity/drawdown charts)
- local research dashboard for ML artifact visualization
- end-to-end ML artifact smoke script (features + returns → signal + report)
- built-in MA crossover and breakout strategy families
- grid search, train/test validation, walk-forward validation
- strategy comparison and permutation diagnostics
- TWSE daily data fetch helpers

## ML Research Workflow

The local ML pipeline runs from fixture features and monthly returns to a
complete v0.2 signal file and HTML report:

```text
features.csv + monthly_returns.csv
  → build_forward_return_labels  →  return_labels.csv
  → join_features_with_return_labels  →  supervised_panel.csv
  → run_factor_diagnostics  →  factor diagnostic artifacts
  → build_ml_dataset  →  dataset.csv
  → fit_baseline_regressor + predict  →  predictions.csv + metrics_summary.json
  → build_ml_prediction_signal  →  ml_signal.csv
  → render_artifact_report  →  report.html
  → local research dashboard
```

The baseline regressor is a closed-form ridge regression using only numpy and
pandas. Missing features are imputed with column medians. Predictions are
converted to quantile-based long/short/neutral signals. Dates with insufficient
cross-sectional dispersion produce all-neutral positions.

## Important Boundaries

- no live trading
- no broker integration
- no profitability guarantee
- no CRSP/WRDS downloader
- no private data committed to the repository
- smoke metrics are integration/regression metrics, not strategy performance claims
- SignalForge integration is file-based; AlphaForge does not import SignalForge runtime code
- OAP characteristics are predictors, not realized returns — labels must come from a separate return source
- dashboard is local-first and reads generated artifacts; it does not upload private data

## Portfolio Summary

- Built a deterministic quantitative research framework that loads market data,
  executes custom-signal and built-in strategies, and writes reproducible
  backtest evidence artifacts
- Integrated external signal sources (OAP asset-pricing characteristics,
  SignalForge v0.2 signal packages) through a standardized `custom_signal`
  file contract with no runtime coupling
- Implemented a local ML research pipeline — feature/label joining, time-based
  train/test splitting, single-factor diagnostics, closed-form ridge regression,
  quantile-based signal conversion, artifact reporting, and local dashboard
  visualization — without requiring sklearn, CRSP, or private data
- Maintains strict data hygiene: private datasets and generated artifacts stay
  out of git; all tests use small deterministic fixtures, with a 500+ test suite
- Designed for extensibility with clear module boundaries across backtesting,
  signal ingestion, factor building, return labeling, ML scaffolding, dashboard
  artifact loading, and artifact reporting

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run commands directly without installing:

```bash
PYTHONPATH=src python3 -m alphaforge.cli --help
```

## Reproducible Smoke Commands

```bash
# Full test suite (500+ tests)
PYTHONPATH=src python3 -m pytest -q

# Convert ML predictions to custom_signal v0.2
PYTHONPATH=src python3 -m alphaforge.cli build-ml-signal \
  --predictions tests/fixtures/ml_signal/predictions.csv \
  --output artifacts/phase24/ml_signal.csv \
  --asset-id-col asset_id \
  --date-col date \
  --prediction-col predicted_return \
  --long-quantile 0.8 \
  --short-quantile 0.2

# End-to-end ML artifact smoke
PYTHONPATH=src python3 scripts/run_ml_artifact_smoke.py \
  --features tests/fixtures/return_labels/features.csv \
  --returns tests/fixtures/return_labels/monthly_returns.csv \
  --output-dir artifacts/phase25/ml_artifact_smoke

# Single-factor diagnostics
PYTHONPATH=src python3 scripts/run_factor_diagnostics.py \
  --panel artifacts/phase25/ml_artifact_smoke/supervised_panel.csv \
  --output-dir artifacts/phase28/mom12m_diagnostics \
  --factor-col Mom12m \
  --label-col ret_fwd_1m \
  --quantiles 5

# Local research dashboard
python -m pip install -e ".[dashboard]"
PYTHONPATH=src streamlit run src/alphaforge/dashboard_app.py
```

## Data Model

### Market Data

OHLCV data for one-symbol backtests:

```text
datetime, open, high, low, close, volume, symbol
```

### Signal Schema

v0.1 (long/flat):

```text
datetime, available_at, symbol, signal_name, signal_value, signal_binary, source
```

`signal_binary` maps to target position `1.0` or `0.0`.

v0.2 (long/flat/short):

```text
datetime, available_at, symbol, asset_id, signal_name, score, direction, target_weight, source
```

`target_weight` must be within `[-1.0, 1.0]`. SignalForge v0.2 requires
`signed_close_to_close_lagged` execution semantics.

### Feature Schema

```text
asset_id, date, <feature columns>
```

### Label Schema

```text
asset_id, date, target_date, horizon_months, ret_fwd_1m, source
```

### Backtest Outputs

```text
metrics_summary.json, equity_curve.csv, trade_log.csv, ranked_results.csv
validation_summary.json, walk_forward_summary.json, permutation_test_summary.json
```

## OAP / Open Source Asset Pricing

AlphaForge processes OAP firm-level characteristics as monthly predictors. No
bundled downloader — place raw files locally under `data/raw/oap/` and keep them
out of git.

The locally verified raw OAP file contains 209 characteristic columns. Current
examples focus on a selected 2010–2012 feature subset including Mom12m, BM,
AssetGrowth, Beta, OperProf, and Investment. Missingness is expected for
firm-level characteristics, especially accounting-based predictors.

Processed files use the convention:

```text
asset_id, date, <feature columns>   (Parquet preferred)
```

## OAP Multi-Factor Signal Builder

Combine multiple OAP feature columns into a v0.2 `signal.csv` via YAML config:

```yaml
features:
  - name: Mom12m
    weight: 1.0
    higher_is_better: true
  - name: BM
    weight: 1.0
    higher_is_better: true
long_quantile: 0.8
short_quantile: 0.2
```

Per date, features are z-score normalized, inverted if needed, and combined into
a weighted score. Top/bottom quantile assets receive long/short target weights.

```bash
PYTHONPATH=src python3 -m alphaforge.cli build-oap-multifactor-signal \
  --features data/processed/oap/oap_panel_2010_2012_features.parquet \
  --config tests/fixtures/oap_multifactor/equal_weight.yaml \
  --output artifacts/phase21/oap_multifactor_signal.csv
```

## Return Label Builder

Convert monthly return panels into forward return labels with month-end alignment.

```bash
PYTHONPATH=src python3 -m alphaforge.cli build-return-labels \
  --returns tests/fixtures/return_labels/monthly_returns.csv \
  --output artifacts/phase22/return_labels.csv \
  --asset-id-col asset_id --date-col date --return-col ret --horizon-months 1
```

Delisting returns are supported via `--delisting-return-col dlret`.

## Single-Factor Diagnostics

Evaluate one factor against forward returns before treating it as a tradable
signal or ML feature. Diagnostics include coverage, missingness, distribution,
IC, Rank IC, quantile forward returns, and top-minus-bottom long-short spread.

```bash
PYTHONPATH=src python3 scripts/run_factor_diagnostics.py \
  --panel artifacts/phase25/ml_artifact_smoke/supervised_panel.csv \
  --output-dir artifacts/phase28/mom12m_diagnostics \
  --factor-col Mom12m \
  --label-col ret_fwd_1m \
  --quantiles 5
```

Outputs: `factor_summary.json`, `factor_coverage_by_date.csv`,
`factor_distribution_by_date.csv`, `factor_ic_timeseries.csv`,
`factor_quantile_returns.csv`, `factor_long_short_spread.csv`.

## ML Baseline Scaffold

Closed-form OLS ridge regression (alpha=1.0), median imputation, standard
scaling. No scikit-learn dependency.

```bash
PYTHONPATH=src python3 -m alphaforge.cli run-ml-baseline \
  --panel tests/fixtures/ml_baseline/supervised_panel.csv \
  --output-dir artifacts/phase23/ml_baseline \
  --label-col ret_fwd_1m --train-end 2024-03-31 \
  --feature-cols Mom12m,BM,Investment
```

Outputs: `dataset.csv`, `predictions.csv`, `metrics_summary.json`.

## sklearn Regression Model Adapters

Optional sklearn-backed regression models (Ridge, Random Forest,
HistGradientBoosting) that output `predictions.csv` compatible with the
Phase 30 ML prediction diagnostics.

Install sklearn support:

```bash
python3 -m pip install -e ".[sklearn]"
```

```bash
PYTHONPATH=src python3 scripts/run_sklearn_ml_model.py \
  --panel tests/fixtures/ml_baseline/supervised_panel.csv \
  --output-dir artifacts/phase32/sklearn_ridge_demo \
  --model ridge_regressor \
  --label-col ret_fwd_1m \
  --train-end 2024-03-31 \
  --feature-cols Mom12m,BM,Investment
```

Outputs: `predictions.csv`, `metrics.json`, `model_summary.json`,
`train_config.json`, `feature_importance.csv`.

Classification models are deferred to a later phase.

## ML Prediction Signal Converter

Converts `predictions.csv` into v0.2 `signal.csv` with quantile-based
long/short/neutral directions. Realized labels are ignored; only predicted scores
drive signal construction.

```bash
PYTHONPATH=src python3 -m alphaforge.cli build-ml-signal \
  --predictions tests/fixtures/ml_signal/predictions.csv \
  --output artifacts/phase24/ml_signal.csv \
  --asset-id-col asset_id --date-col date \
  --prediction-col predicted_return \
  --long-quantile 0.8 --short-quantile 0.2
```

## End-to-End ML Artifact Smoke

Runs the full pipeline from fixtures: features + returns → labels → dataset →
model → predictions → v0.2 signal → HTML report. Proves integration, not
strategy profitability.

```bash
PYTHONPATH=src python3 scripts/run_ml_artifact_smoke.py \
  --features tests/fixtures/return_labels/features.csv \
  --returns tests/fixtures/return_labels/monthly_returns.csv \
  --output-dir artifacts/phase25/ml_artifact_smoke
```

Generates: `return_labels.csv`, `supervised_panel.csv`, `dataset.csv`,
`predictions.csv`, `metrics_summary.json`, `ml_signal.csv`, `report.html`,
`smoke_summary.json`.

## Local Research Dashboard

The dashboard visualizes a generated artifact directory without uploading private
data. It displays pipeline file status, JSON summaries, table shapes/previews,
and the generated HTML report.

```bash
python -m pip install -e ".[dashboard]"
PYTHONPATH=src streamlit run src/alphaforge/dashboard_app.py
```

Default artifact directory:

```text
artifacts/phase25/ml_artifact_smoke
```

See `docs/phase-27-local-research-dashboard.md` for the full Phase 27 boundary
and validation commands.

## SignalForge Integration

AlphaForge consumes SignalForge v0.2 packages through file artifacts — no
runtime import of SignalForge internals.

A package directory contains `market_data.csv`, `signal.csv`,
`signal_contract.yaml`, `data_quality_report.json`, and `manifest.json`.
AlphaForge validates the manifest, loads the signal through `custom_signal` v0.2,
and runs a signed long/short smoke backtest.

```bash
PYTHONPATH=src python3 -m alphaforge.cli smoke-signalforge-package \
  --package sample_data/signalforge/demo_v02_package
```

For `custom_signal`, AlphaForge treats the supplied signal as frozen external
input. It validates schema and alignment, then runs development/holdout
evaluation and walk-forward validation — but does not perform parameter search
over SignalForge internals.

## HTML Artifact Reports

Standalone HTML reports with Plotly equity/drawdown charts, metric cards, and
trade log tables.

```bash
PYTHONPATH=src python3 -m alphaforge.cli render-artifact-report \
  --artifact-dir outputs/some_run --output outputs/some_run/report.html
```

The renderer reads whatever artifacts are present and reports missing files
gracefully.

## Built-In Strategies

MA crossover and breakout strategy families with grid search, train/test
validation, walk-forward, and permutation diagnostics.

```bash
PYTHONPATH=src python3 -m alphaforge.cli run \
  --data sample_data/sample_ohlcv.csv --symbol SAMPLE \
  --short-window 2 --long-window 4

PYTHONPATH=src python3 -m alphaforge.cli search \
  --data sample_data/sample_ohlcv.csv --symbol SAMPLE \
  --short-windows 2 3 --long-windows 4 5 --experiment-name sample_search
```

## Testing

```bash
PYTHONPATH=src python3 -m pytest -q            # full suite
PYTHONPATH=src python3 -m pytest -q -x          # stop on first failure
```

All tests use small deterministic fixtures under `tests/fixtures/`.

## Data Hygiene

Do not commit private datasets or generated artifacts. The following stay ignored:

```text
artifacts/   data/raw/   data/processed/   data/**/*.csv   data/**/*.parquet   outputs/
```

Checked-in fixtures under `tests/fixtures/` and `sample_data/` are small and
intended for deterministic tests.

## Limitations

- one-symbol `custom_signal` validation at runtime
- no CRSP/WRDS downloader or real-time data feeds
- no committed raw or processed OAP data
- baseline ML only — no deep learning or advanced model architectures
- signal quantile-based conversion requires cross-sectional dispersion; thin dates become neutral
- dashboard is a local artifact viewer, not a hosted multi-user platform

## Roadmap

- extend ML baseline with cross-validation and regularization paths
- add factor diagnostics outputs to the dashboard
- add ML prediction diagnostics
- add portfolio/exposure diagnostics to the dashboard
- add multi-symbol custom_signal validation
- formalize local loaders for processed OAP Parquet files
- keep SignalForge package compatibility aligned with v0.2 contract
