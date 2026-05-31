# Phase 56: Interview Streamlit Showcase

Phase 56 adds a read-only Streamlit showcase for already-generated AlphaForge interview artifacts.

It is intended for internship interviews where a dashboard is more intuitive than opening raw JSON and CSV files. The app combines Streamlit's run selection / deployability with embedded HTML report support.

## What it does

The showcase reads an artifact run directory and displays:

- run overview
- demo health checks
- ML signal exposure by symbol, including a donut chart
- cross-sectional signal table
- projected single-symbol validation signal
- prediction table and predicted-vs-realized scatter
- final-holdout metrics
- final-holdout equity curve and drawdown
- final-holdout trade log
- embedded HTML artifact report
- artifact trace
- project boundaries

## Artifact source options

The sidebar supports two source modes:

```text
Local artifact run
Upload artifact ZIP
```

### Local artifact run

The app discovers compatible runs under:

```text
artifacts/demo
```

A compatible run is any directory containing either:

```text
ml_demo_summary.json
research_validation/ml_demo_research_validation_summary.json
```

You can also enter a custom path manually.

### Upload artifact ZIP

For Streamlit Cloud or interview laptops where the artifact run is not already on disk, you can upload a ZIP file containing a run directory.

The upload path is extracted under:

```text
artifacts/uploaded_showcase_runs
```

ZIP extraction rejects unsafe paths that try to escape the upload directory.

## Embedded HTML showcase

The app includes an `HTML Showcase` tab. If the artifact run contains:

```text
interview_artifact_report.html
```

it is embedded directly inside Streamlit using Streamlit components.

This lets the app combine:

```text
Streamlit shell: run selection, upload, tabs, deployment
HTML report: richer strategy-style layout and static artifact view
```

## What it does not do

The showcase does not:

- train models
- generate predictions
- build signals
- run research validation
- download market data
- execute live trades

It only reads files that already exist under an artifact directory or an uploaded artifact ZIP.

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

For a real-data interview run, generate artifacts locally and then either:

```text
1. point the sidebar to artifacts/demo/real_data_interview_run
2. upload a ZIP containing the real-data artifact run
```

Do not commit licensed raw market data to the public repository. Prefer sharing derived, permission-safe artifacts or uploading a private ZIP during the demo.

## Recommended interview workflow

1. Run the pipeline before the interview.
2. Confirm the health checks pass.
3. Open the Streamlit showcase.
4. Select the artifact run or upload the ZIP.
5. Present the dashboard sections in this order:

```text
Run Overview
→ Demo Health Checks
→ Signal / Exposure
→ Predictions
→ Final Holdout
→ HTML Showcase
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
