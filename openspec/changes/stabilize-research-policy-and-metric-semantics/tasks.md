# Tasks

## 1. OpenSpec

- [x] 1.1 Create proposal, design, tasks, and spec delta artifacts.
- [x] 1.2 Validate the OpenSpec change.

## 2. Implementation

- [x] 2.1 Update `ResearchPolicyConfig` default p-value semantics and p-value validation.
- [x] 2.2 Add `bar_count` to `MetricReport` and compute it in `metrics.py`.
- [x] 2.3 Switch Sharpe to sample standard deviation with safe edge-case handling.
- [x] 2.4 Normalize turnover penalty by backtest length in `scoring.py`.
- [x] 2.5 Update walk-forward Sharpe handling to avoid treating mean Sharpe as pooled.
- [x] 2.6 Add the permutation reconstruction caveat comment.

## 3. Tests

- [x] 3.1 Add research-policy tests for above-threshold, boundary, missing-p-value, and explicit opt-out cases.
- [x] 3.2 Add metric tests for `ddof=1`, short/degenerate return series, and `bar_count`.
- [x] 3.3 Add scoring tests showing turnover normalization across different backtest lengths.
- [x] 3.4 Update walk-forward aggregation and policy tests for pooled-versus-mean Sharpe semantics.
- [x] 3.5 Update serialization/storage tests for the `MetricReport` schema change.

## 4. Verification

- [x] 4.1 Run `openspec validate stabilize-research-policy-and-metric-semantics --type change --no-interactive`.
- [x] 4.2 Run `pytest`.
- [x] 4.3 Log meaningful implementation and verification steps to Obsidian.
