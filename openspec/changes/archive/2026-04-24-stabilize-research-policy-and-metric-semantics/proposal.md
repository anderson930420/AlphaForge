# Proposal: stabilize-research-policy-and-metric-semantics

## Boundary problem

- Research-policy guardrails currently leave permutation p-value enforcement opt-in by default, which makes the default promotion path less strict than the validation semantics now expect.
- Metric semantics still compute Sharpe with population standard deviation and apply turnover as a cumulative penalty, which can distort scores for longer backtests.
- Walk-forward aggregation exposes only a mean Sharpe ratio, but a mean of fold-level Sharpe values is not a decision-grade pooled statistic.
- The permutation null reconstruction is path dependent and should remain explicitly non-vectorized, with a caution that the current reconstruction is only acceptable for close-only strategies.

## Canonical ownership decision

- `src/alphaforge/research_policy.py` owns promotion/rejection guardrails.
- `src/alphaforge/schemas.py` owns runtime contracts, including metric and permutation summary fields.
- `src/alphaforge/metrics.py` owns performance analytics semantics.
- `src/alphaforge/scoring.py` owns ranking/scoring logic and must consume metrics without redefining formulas.
- `src/alphaforge/walk_forward_aggregation.py` owns aggregate walk-forward summaries.
- `src/alphaforge/permutation.py` owns permutation/null construction and must keep the reconstruction path dependent.
- `src/alphaforge/experiment_runner.py` remains orchestration-only.

## Scope

- Set `ResearchPolicyConfig.max_permutation_p_value` default to `0.05`.
- Preserve `None` as an explicit caller opt-out for permutation p-value enforcement.
- Reject candidates whose permutation p-value exceeds the configured maximum.
- Reject candidates when a required permutation summary is present but its p-value is missing.
- Add `bar_count` to `MetricReport` and compute it from the equity-curve length.
- Update Sharpe to use sample standard deviation with safe zero/NaN handling.
- Normalize turnover penalty by backtest length in scoring.
- Add a walk-forward Sharpe aggregate that distinguishes a true pooled statistic from the descriptive mean, and do not treat the mean as decision-grade when pooled data is unavailable.
- Keep permutation reconstruction non-vectorized and document the close-only caveat.
- Update serialization and storage tests for the metric schema change.

## Explicitly out of scope

- GA
- ML
- new strategies
- UI
- broker API
- broad refactors
- persistence format changes beyond the metric schema update already required here

## Migration risk

- The metric schema gains one new runtime field, so any persisted artifact tests that snapshot metric payloads must be updated.
- Walk-forward policy behavior may become more conservative if no pooled Sharpe statistic is available from the current fold summary contract.
- Research policy callers that intentionally pass `max_permutation_p_value=None` will still opt out, but callers that rely on the default config will now enforce the 0.05 threshold.

## Acceptance conditions

- OpenSpec validates for `stabilize-research-policy-and-metric-semantics`.
- P-value enforcement rejects above-threshold candidates and allows at-or-below-threshold candidates when other checks pass.
- Missing permutation p-values fail when permutation evidence is required.
- `MetricReport.bar_count` is persisted and used by scoring.
- Sharpe uses `ddof=1` and handles short or degenerate return series safely.
- Walk-forward aggregation does not rely on mean Sharpe as a decision-grade pooled statistic.
- Full pytest passes.
