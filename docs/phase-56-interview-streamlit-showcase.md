# Phase 56: Interview Streamlit Showcase

Phase 56 adds a read-only Streamlit viewer for already-generated AlphaForge interview artifacts.

It is intended for internship interviews where a dashboard is more intuitive than opening raw JSON and CSV files.

## What it does

The showcase reads an artifact run directory and displays:

- run overview
- demo health checks
- ML signal exposure by symbol
- cross-sectional signal table
- projected single-symbol validation signal
- prediction table and predicted-vs-realized scatter
- final-holdout metrics
- final-holdout equity curve
- final-holdout trade log
- artifact trace
- project boundaries

## What it does not do

The showcase does not:

- train models
- generate predictions
- build signals
- run research validation
- download market data
- execute live trades

It only reads files that already exist under an artifact directory.

## Generate the default demo artifacts

```bash
bash scripts/run_interview_demo.sh artifacts/demo/interview_ml_demo_C
```

This generates the default artifact run used by the showcase and verifies:

```text
nonzero_target_weight_count > 0
extra_signal_dates == []
```

## Launch the showcase

Install dashboard dependencies:

```bash
python3 -m pip install -e ".[dashboard]"
```

Run the app:

```bash
PYTHONPATH=src streamlit run src/alphaforge/interview_showcase_app.py
```

The default artifact directory is:

```text
artifacts/demo/interview_ml_demo_C
```

You can change the artifact directory from the sidebar. For a real-data interview run, point the sidebar to something like:

```text
artifacts/demo/real_data_interview_run
```

## Recommended interview workflow

1. Run the pipeline before the interview.
2. Confirm the health checks pass.
3. Open the Streamlit showcase.
4. Present the dashboard sections in this order:

```text
Run Overview
→ Demo Health Checks
→ ML Signal and Exposure
→ Predictions
→ Final Holdout
→ Artifact Trace
→ Boundaries
```

## Interpretation guidance

Do not present fixture results as profitable alpha.

Correct interpretation:

```text
This dashboard proves that the ML research loop is reproducible and artifact-backed:
features → labels → model predictions → signal contract → research validation → final holdout artifacts.
```

The dashboard is strongest as evidence of ML research engineering, not as evidence of a live trading system.

## Testing

```bash
PYTHONPATH=src python3 -m pytest tests/test_interview_showcase.py -q
```
