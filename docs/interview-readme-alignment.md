# Interview README Alignment

This document defines the interview-facing positioning for AlphaForge.

Use it to align the README, portfolio description, and interview narration around ML engineering rather than around claims of trading profitability.

## Positioning statement

```text
AlphaForge is a reproducible ML-oriented quantitative research framework.
It connects feature engineering, forward-return labeling, sklearn/PyTorch baselines,
prediction diagnostics, signal construction, research validation, and model comparison
into a traceable artifact pipeline.
```

## What to emphasize

### 1. ML research workflow

```text
features + returns
  → forward-return labels
  → supervised ML panel
  → regression / classification baselines
  → prediction diagnostics
  → signal construction
  → research validation
  → model comparison
  → reproducible artifacts
```

The main value is not a single strategy result. The main value is that the ML research loop is connected and reproducible.

### 2. Time-aware validation

Highlight:

- forward-return label construction
- time-based train/test split
- lagged close-to-close execution semantics
- development / holdout research-validation split

This shows that the project treats time-series ML differently from ordinary random-split supervised learning.

### 3. Leakage prevention and artifact discipline

Highlight:

- feature / label separation
- prediction and output columns excluded from feature inference
- JSON-safe metric artifacts
- deterministic fixtures and regression tests
- generated artifacts kept out of git

This is the strongest ML-engineering story for interviews.

### 4. Model coverage

Current ML coverage:

- closed-form ridge baseline without sklearn
- sklearn regression adapters: Ridge, Random Forest, HistGradientBoosting
- PyTorch MLP baseline
- sklearn classifier baseline with predicted probabilities
- model comparison report builder

Do not present this as a search for the most profitable model. Present it as a framework for comparing model families under a consistent artifact contract.

### 5. SignalForge interface

SignalForge is the upstream signal-generation layer. AlphaForge is the research-validation backend.

The projects communicate through a file-based v0.2 custom_signal contract:

```text
SignalForge
  → market_data.csv
  → signal.csv
  → signal_contract.yaml
  → data_quality_report.json
  → manifest.json
  → AlphaForge smoke-signalforge-package / custom_signal research validation
```

The important architectural point is low runtime coupling: AlphaForge consumes files and does not import SignalForge internals.

## Boundaries to keep explicit

Keep these limitations visible. They make the project more credible, not weaker.

```text
- not live trading
- not broker integration
- not production execution
- not claiming alpha from synthetic fixtures
- generated demo metrics are integration evidence, not strategy performance claims
- currently one-symbol custom_signal validation at runtime
- multi-symbol portfolio validation is future work
- SignalForge integration is file-based; AlphaForge does not import SignalForge runtime code
- private or real market datasets should stay out of git
```

## Suggested README structure

```text
1. Project positioning
2. ML research workflow
3. Current capabilities
4. Interview demo command
5. Artifact showcase
6. SignalForge integration
7. Boundaries
8. Roadmap
```

## Suggested interview narration

```text
I built AlphaForge as an ML-oriented quant research framework, not as a live trading bot.
The goal is to make the research loop reproducible: features and returns become forward-return labels,
labels become supervised datasets, models produce predictions, predictions are diagnosed and converted
into signal contracts, and those signals can be validated through a consistent research protocol.

SignalForge is the upstream signal-generation project. It emits standardized v0.2 signal packages,
and AlphaForge consumes those packages without importing SignalForge runtime code. That gives the two
projects a clean contract boundary.

The current demo uses deterministic fixtures, so I do not claim that the fixture Sharpe or return proves alpha.
The demo proves that the ML workflow is connected, contract-checked, and reproducible from data inputs to
final holdout artifacts.
```
