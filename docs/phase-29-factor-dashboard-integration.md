# Phase 29 — Factor Diagnostics Dashboard Integration

## Goal

Phase 29 connects Phase 28 single-factor diagnostic artifacts to the local research dashboard.

The dashboard now reads:

```text
artifacts/phase25/ml_artifact_smoke
artifacts/phase28/mom12m_diagnostics_q2
```

The first directory contains ML pipeline artifacts. The second directory contains factor diagnostic artifacts.

## Usage

Generate ML smoke artifacts:

```bash
PYTHONPATH=src python3 scripts/run_ml_artifact_smoke.py \
  --features tests/fixtures/return_labels/features.csv \
  --returns tests/fixtures/return_labels/monthly_returns.csv \
  --output-dir artifacts/phase25/ml_artifact_smoke
```

Generate factor diagnostics:

```bash
PYTHONPATH=src python3 scripts/run_factor_diagnostics.py \
  --panel artifacts/phase25/ml_artifact_smoke/supervised_panel.csv \
  --output-dir artifacts/phase28/mom12m_diagnostics_q2 \
  --factor-col Mom12m \
  --label-col ret_fwd_1m \
  --quantiles 2
```

Run the dashboard:

```bash
python3 -m pip install -e ".[dashboard]"
PYTHONPATH=src streamlit run src/alphaforge/dashboard_app.py
```

## Added dashboard views

- factor diagnostic artifact status
- factor summary cards
- coverage by date
- IC and Rank IC by date
- quantile forward returns
- long-short spread

## Boundary

This phase only visualizes existing factor diagnostic artifacts. It does not recompute diagnostics, train models, run backtests, or modify signal construction.

## Validation

```bash
git diff --check
PYTHONPATH=src python3 -m pytest tests/test_dashboard_factor_artifacts.py -q
PYTHONPATH=src python3 -m pytest tests/test_dashboard_artifacts.py -q
PYTHONPATH=src python3 -m pytest -q
```
