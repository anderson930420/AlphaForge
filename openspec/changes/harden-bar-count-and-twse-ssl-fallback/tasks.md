# Tasks

## 1. OpenSpec

- [x] 1.1 Create proposal, design, tasks, and spec delta artifacts.
- [x] 1.2 Validate the OpenSpec change.

## 2. Implementation

- [x] 2.1 Make `MetricReport.bar_count` required and positive.
- [x] 2.2 Fail fast in `scoring.py` for invalid `bar_count`.
- [x] 2.3 Keep `compute_metrics()` producing valid `bar_count` values and reject empty equity curves.
- [x] 2.4 Harden TWSE SSL fallback logging and local warning suppression.
- [x] 2.5 Clarify walk-forward `mean_test_sharpe_ratio` descriptive-only semantics.

## 3. Tests

- [x] 3.1 Add schema and scoring regression tests for valid and invalid `bar_count`.
- [x] 3.2 Add metric tests for positive `bar_count` and empty equity-curve rejection.
- [x] 3.3 Add TWSE tests for verified request path, SSL fallback warning, and local warning suppression.
- [x] 3.4 Keep walk-forward policy regression coverage for pooled Sharpe semantics.

## 4. Verification

- [x] 4.1 Run `grep -R "mean_test_sharpe" -n src/alphaforge`.
- [x] 4.2 Run `openspec validate harden-bar-count-and-twse-ssl-fallback --type change --no-interactive`.
- [x] 4.3 Run `pytest -q`.
- [x] 4.4 Log meaningful implementation and verification steps to Obsidian.
