# Interview Demo Artifact Showcase

This guide explains how to present AlphaForge as a reproducible ML-oriented quantitative research workflow.

The demo uses deterministic fixtures. It proves that the pipeline and artifact contracts work end-to-end; it is not evidence of profitable alpha.

## One-command demo

```bash
bash scripts/run_interview_demo.sh
```

Optional custom output directory:

```bash
bash scripts/run_interview_demo.sh artifacts/demo/my_interview_demo
```

The script runs:

```text
features + returns
  → forward-return labels
  → supervised ML panel
  → ridge regression predictions
  → prediction diagnostics
  → cross-sectional ML signal
  → single-symbol projection for symbol C
  → custom_signal research validation
  → final-holdout artifact report HTML
```

## Built-in demo health checks

The script reads `research_validation/ml_demo_research_validation_summary.json` and fails fast if:

```text
nonzero_target_weight_count <= 0
extra_signal_dates != []
```

These checks protect the live demo from two common failures:

- all-flat selected symbol: the projected signal has no exposure and produces a flat equity line
- date mismatch: signal dates are not present in market data and would violate custom_signal alignment

The current demo intentionally uses symbol `C`, not `A`, because `C` has nonzero exposure in the fixture-generated ML signal.

## Key artifacts to show

### 1. Pipeline summary

```text
artifacts/demo/interview_ml_demo_C/ml_demo_summary.json
```

Use this to show that research validation was enabled:

```json
"does_run_research_validation": true
```

### 2. Generated ML signal

```text
artifacts/demo/interview_ml_demo_C/signal/ml_signal.csv
```

Use this to explain cross-sectional signal construction:

```text
predicted_return scores
→ long / short / neutral target weights
→ custom_signal v0.2 rows
```

### 3. Research-validation summary

```text
artifacts/demo/interview_ml_demo_C/research_validation/ml_demo_research_validation_summary.json
```

Use this to show the demo health checks:

```text
nonzero_target_weight_count > 0
all_flat_selected_symbol = false
extra_signal_dates = []
warnings = []
```

### 4. Final-holdout metrics

```text
artifacts/demo/interview_ml_demo_C/research_validation/ml_signal_single_symbol_validation/final_holdout/metrics_summary.json
```

Use this to show that the signal actually reached AlphaForge's validation layer and produced final-holdout metrics.

Do not present the synthetic fixture metrics as real alpha. Present them as proof that the workflow produces reproducible validation artifacts.

### 5. Standalone HTML artifact report

```text
artifacts/demo/interview_ml_demo_C/interview_artifact_report.html
```

The one-command demo renders this automatically with:

```bash
PYTHONPATH=src python3 -m alphaforge.cli render-artifact-report \
  --artifact-dir artifacts/demo/interview_ml_demo_C/research_validation/ml_signal_single_symbol_validation/final_holdout \
  --output artifacts/demo/interview_ml_demo_C/interview_artifact_report.html
```

Open this HTML file during the interview instead of walking through many JSON files.

## Suggested interview narration

```text
AlphaForge is not a live trading bot. It is a reproducible ML research pipeline.
The demo starts from feature and return fixtures, builds forward-return labels,
trains a ridge regression baseline, generates predictions, converts predictions
into a custom_signal v0.2 target-weight file, projects the signal to one symbol,
and runs it through the same custom-signal research-validation protocol used by
non-ML strategies.

The key point is not that this synthetic fixture proves alpha. The key point is
that the ML workflow is reproducible, contract-checked, and produces traceable
artifacts from labels to final-holdout validation.
```

## What to avoid claiming

Do not claim:

- the fixture result proves profitable alpha
- AlphaForge is a live trading system
- the current custom_signal validator is a full multi-symbol portfolio engine
- synthetic fixture Sharpe or annualized return is statistically meaningful

Correct claim:

```text
This demo proves that the ML research loop is closed and reproducible:
features → labels → model → predictions → signal → research validation → artifacts.
```
