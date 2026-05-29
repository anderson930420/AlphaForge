# Phase 31 — ML Prediction Diagnostics Dashboard Integration

## Goal

Phase 31 connects Phase 30 ML prediction diagnostic artifacts to the local research dashboard.

The dashboard now reads a third local artifact directory:

```text
ML prediction diagnostics directory
```

Default:

```text
artifacts/phase30b/synthetic_prediction_demo/ml_prediction_diagnostics
```

## Usage

Generate synthetic prediction demo artifacts:

```bash
PYTHONPATH=src python3 scripts/run_synthetic_prediction_demo.py \
  --output-dir artifacts/phase30b/synthetic_prediction_demo \
  --months 12 \
  --assets 20 \
  --quantiles 5
```

Run the dashboard:

```bash
python3 -m pip install -e ".[dashboard]"
PYTHONPATH=src streamlit run src/alphaforge/dashboard_app.py
```

## Added dashboard views

- ML prediction diagnostic artifact status
- prediction summary cards
- Prediction IC / Rank IC time series
- prediction quantile forward returns
- prediction long-short spread
- prediction error by date

## Boundary

This phase only visualizes existing ML prediction diagnostic artifacts. It does not recompute diagnostics, train models, run backtests, or modify signal construction.

## Validation

```bash
git diff --check
PYTHONPATH=src python3 -m pytest tests/test_dashboard_ml_predictions.py -q
PYTHONPATH=src python3 -m pytest tests/test_ml_demo_artifacts.py -q
PYTHONPATH=src python3 -m pytest -q
```
