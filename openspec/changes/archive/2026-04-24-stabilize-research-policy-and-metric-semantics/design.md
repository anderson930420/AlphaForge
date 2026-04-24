# Design: stabilize-research-policy-and-metric-semantics

## Decision

Apply a narrowly scoped semantic cleanup across the existing AlphaForge architecture boundaries:

- `schemas.py` gains `MetricReport.bar_count` and permits a missing permutation p-value in `PermutationTestSummary` so guardrails can reject missing evidence explicitly.
- `metrics.py` computes `bar_count`, uses sample standard deviation for Sharpe, and returns `0.0` for undersized or degenerate return series.
- `scoring.py` normalizes turnover penalty by the number of bars instead of the cumulative turnover total.
- `research_policy.py` defaults to a 0.05 permutation p-value threshold and treats `None` as an intentional opt-out only when explicitly configured.
- `walk_forward_aggregation.py` keeps the descriptive fold mean but does not let the mean stand in for a pooled Sharpe statistic.
- `policy.py` must not promote walk-forward candidates based on mean Sharpe alone when no pooled Sharpe statistic is available.
- `permutation.py` keeps the path-dependent reconstruction loop and documents why it stays that way.

## Data contracts

### `MetricReport`

- `bar_count: int`

### `ResearchPolicyConfig`

- `max_permutation_p_value: float | None = 0.05`
- `None` means the caller intentionally disabled permutation p-value enforcement.

### `PermutationTestSummary`

- `empirical_p_value: float | None`
- `None` represents a missing p-value and must fail when p-value enforcement is enabled.

## Metric semantics

### Sharpe ratio

- Use `returns.std(ddof=1)`.
- Return `0.0` when there are fewer than 2 returns.
- Return `0.0` when the sample standard deviation is NaN or zero.

### Turnover penalty

- Use `turnover_per_bar = metrics.turnover / max(metrics.bar_count, 1)`.
- Apply `turnover_penalty = turnover_per_bar * 0.01`.

## Research policy semantics

- Above-threshold permutation p-values reject the candidate.
- At-or-below-threshold permutation p-values can pass when all other configured checks pass.
- Missing p-values fail whenever permutation summary evidence is required by the active policy config.
- Explicit `None` disables p-value enforcement only when the caller sets it.

## Walk-forward Sharpe semantics

- The current fold summary contract only carries scalar fold metrics, so a true pooled Sharpe ratio is not derivable from the current data alone.
- The aggregate helper may continue returning the descriptive mean for display, but policy code must not treat that mean as a statistically authoritative promotion criterion.
- If a future richer fold contract provides return-series data or equivalent sufficient statistics, a `pooled_test_sharpe_ratio` can be added without changing the policy shape.

## Permutation reconstruction

- The reconstruction loop must remain path dependent and is acceptable as an `itertuples()` loop.
- The current high/low reconstruction is acceptable for close-only strategies because the synthetic path is reconstructed from relative movement blocks.
- This null model must be revisited before it is used for high/low-dependent strategies such as ATR, stop-loss, or intrabar breakout logic.

## Out of scope

- GA
- ML
- new strategies
- UI
- broker API
- broad refactors
- full walk-forward return-series pooling
