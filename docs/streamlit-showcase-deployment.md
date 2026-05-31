# Streamlit Showcase Deployment

This guide explains how to deploy the AlphaForge Interview Showcase and how to package artifact runs for demos.

The showcase is designed to read already-generated artifacts. It does not train models, run backtests, download market data, or execute trades.

## Entrypoint

For Streamlit Cloud, use the root-level entrypoint:

```text
streamlit_app.py
```

For local development, either command works:

```bash
PYTHONPATH=src streamlit run src/alphaforge/interview_showcase_app.py
streamlit run streamlit_app.py
```

## Requirements

Use:

```text
requirements-streamlit.txt
```

It installs AlphaForge with the dashboard extra:

```text
-e .[dashboard]
```

## Local demo workflow

Generate the deterministic demo artifacts:

```bash
bash scripts/run_interview_demo.sh artifacts/demo/interview_ml_demo_C
```

Launch the app:

```bash
streamlit run streamlit_app.py
```

Then select:

```text
Local artifact run → artifacts/demo/interview_ml_demo_C
```

## Package an artifact run as ZIP

Use:

```bash
bash scripts/package_interview_artifacts.sh \
  artifacts/demo/interview_ml_demo_C \
  artifacts/demo/interview_ml_demo_C.zip
```

The script checks that required artifacts exist and verifies:

```text
nonzero_target_weight_count > 0
extra_signal_dates == []
```

It also requires:

```text
interview_artifact_report.html
```

unless you pass:

```bash
--allow-missing-html
```

## Streamlit Cloud workflow

1. Deploy this repository on Streamlit Cloud.
2. Set the app entrypoint to:

```text
streamlit_app.py
```

3. Use `requirements-streamlit.txt` for dependencies.
4. Open the deployed app.
5. Use the sidebar mode:

```text
Upload artifact ZIP
```

6. Upload a package created by `scripts/package_interview_artifacts.sh`.

## Real-data interview workflow

After running a real-data pipeline locally, package only the derived artifact run:

```bash
bash scripts/package_interview_artifacts.sh \
  artifacts/demo/real_data_interview_run \
  artifacts/demo/real_data_interview_run.zip
```

Then upload the ZIP in the Streamlit app.

## Data policy

Do not commit licensed or private raw market data to the public repository.

Prefer:

```text
raw data stays local
→ pipeline generates derived artifacts
→ package derived artifacts as ZIP
→ upload ZIP during demo
```

Before sharing any real-data artifact bundle, confirm that the files do not contain restricted raw data or license-protected redistribution content.

## What to present

Recommended order:

```text
Overview
→ Health Checks
→ Signal / Exposure
→ Predictions
→ Final Holdout
→ HTML Showcase
→ Artifact Trace
→ Boundaries
```

Key message:

```text
The demo proves that the ML research workflow is reproducible and artifact-backed.
It does not claim profitable alpha from a single fixture or small-sample run.
```
