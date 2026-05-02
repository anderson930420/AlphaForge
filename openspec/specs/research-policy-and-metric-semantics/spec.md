# research-policy-and-metric-semantics Specification

## Purpose
TBD - created by archiving change stabilize-research-policy-and-metric-semantics. Update Purpose after archive.
## Requirements
### Requirement: Research policy enforces permutation p-values by default

AlphaForge SHALL default `ResearchPolicyConfig.max_permutation_p_value` to `0.05` and SHALL treat `None` as an explicit caller opt-out only.

#### Purpose

- Make the default research-policy path strict enough to protect permutation validity.
- Keep intentional opt-outs possible for workflows that do not supply permutation evidence.

#### Canonical owner

- `src/alphaforge/research_policy.py` is authoritative for this guardrail.

#### Scenario: candidates above the default p-value threshold are rejected

- GIVEN a candidate with a permutation summary whose empirical p-value is greater than `0.05`
- AND no other configured checks fail
- WHEN the research policy evaluator runs with the default config
- THEN the decision SHALL reject the candidate

#### Scenario: candidates at or below the threshold can still pass

- GIVEN a candidate with a permutation summary whose empirical p-value is less than or equal to `0.05`
- AND all other configured checks pass
- WHEN the research policy evaluator runs with the default config
- THEN the decision SHALL promote the candidate

#### Scenario: explicit opt-out disables p-value enforcement

- GIVEN a caller intentionally sets `max_permutation_p_value=None`
- WHEN the research policy evaluator runs
- THEN the p-value check SHALL be skipped

#### Scenario: missing p-values fail when permutation evidence is required

- GIVEN permutation summary evidence is required by the active policy config
- AND the permutation summary has no empirical p-value
- WHEN the research policy evaluator runs
- THEN the decision SHALL reject the candidate
- AND the decision SHALL record the missing p-value in its reasons

### Requirement: MetricReport carries bar-count semantics used by scoring

AlphaForge SHALL include `bar_count` in `MetricReport` and SHALL populate it from the equity-curve length when metrics are computed.

#### Purpose

- Normalize turnover-based penalties by backtest duration.
- Keep the runtime contract explicit instead of burying bar count in metadata.

#### Canonical owner

- `src/alphaforge/schemas.py` owns the runtime contract.
- `src/alphaforge/metrics.py` owns the computed value.

#### Scenario: computed metrics include bar count

- GIVEN a non-empty equity curve
- WHEN metrics are computed
- THEN the resulting `MetricReport` SHALL include the equity-curve length as `bar_count`

### Requirement: Sharpe ratio uses sample standard deviation

AlphaForge SHALL compute Sharpe using `returns.std(ddof=1)` and SHALL return `0.0` when there are fewer than 2 returns, when the sample standard deviation is NaN, or when the sample standard deviation is zero.

#### Purpose

- Align Sharpe with sample-statistics semantics.
- Avoid division-by-zero or NaN propagation for undersized return series.

#### Canonical owner

- `src/alphaforge/metrics.py`

#### Scenario: sample standard deviation is used

- GIVEN a return series with at least two observations
- WHEN Sharpe is computed
- THEN the sample standard deviation SHALL be used

#### Scenario: degenerate series return zero Sharpe

- GIVEN a return series with fewer than two observations, or with NaN or zero sample standard deviation
- WHEN Sharpe is computed
- THEN the result SHALL be `0.0`

### Requirement: Turnover penalty is normalized by backtest length

AlphaForge SHALL compute scoring turnover penalties using turnover per bar instead of cumulative turnover.

#### Purpose

- Avoid penalizing longer backtests solely because they span more bars.

#### Canonical owner

- `src/alphaforge/scoring.py`

#### Scenario: equal average turnover across different lengths yields equivalent penalty

- GIVEN two metric reports with the same turnover per bar but different bar counts
- WHEN scores are computed
- THEN the turnover penalty contribution SHALL be the same for both reports

### Requirement: Walk-forward aggregation does not treat mean Sharpe as pooled Sharpe

AlphaForge SHALL distinguish a descriptive mean fold Sharpe from a decision-grade pooled Sharpe statistic.

#### Purpose

- Prevent the mean of fold Sharpe ratios from being treated as a statistically authoritative aggregate.
- Preserve room for a future pooled statistic when richer return-series data becomes available.

#### Canonical owner

- `src/alphaforge/walk_forward_aggregation.py`
- `src/alphaforge/policy.py`

#### Limitation

- The current fold-summary contract does not carry enough return-series information to compute a true pooled Sharpe ratio from the currently available data alone.
- The aggregate helper MAY continue reporting `mean_test_sharpe_ratio` as a descriptive value.
- Policy code MUST NOT treat `mean_test_sharpe_ratio` as the decision-grade pooled statistic.

#### Scenario: mean Sharpe is not used as the pooled decision statistic

- GIVEN walk-forward aggregate test metrics that do not supply a pooled Sharpe statistic
- WHEN walk-forward policy evaluation runs
- THEN the policy SHALL not validate candidates on the basis of mean Sharpe alone

#### Scenario: a future pooled Sharpe can be consumed if present

- GIVEN walk-forward aggregate test metrics that include `pooled_test_sharpe_ratio`
- WHEN policy evaluation runs
- THEN the pooled value MAY be used as the decision-grade Sharpe statistic

### Requirement: Permutation reconstruction remains path dependent and close-only aware

AlphaForge SHALL keep `_reconstruct_market_data_from_relative_rows` path dependent and SHALL document that the current high/low reconstruction is acceptable for close-only strategies but must be revisited for strategies that depend on intrabar extremes.

#### Purpose

- Preserve the correctness of the null model for path-dependent reconstruction.
- Avoid accidental vectorization that would obscure the sequential reconstruction logic.

#### Canonical owner

- `src/alphaforge/permutation.py`

#### Scenario: reconstruction stays sequential

- GIVEN relative OHLC rows that need to be reconstructed into a synthetic market path
- WHEN the null model is built
- THEN the reconstruction SHALL remain sequential/path dependent

#### Scenario: close-only strategies remain in scope

- GIVEN a strategy that only consumes close-based logic
- WHEN the current permutation null model is used
- THEN the current high/low reconstruction MAY be considered acceptable

#### Scenario: intrabar strategies require a revisit

- GIVEN a strategy that depends on ATR, stop-loss, or intrabar breakout logic
- WHEN the permutation null model is considered
- THEN the implementation SHALL be revisited before use

### Requirement: win rate is computed from positive trade net returns

`src/alphaforge/metrics.py` SHALL compute `win_rate` as the fraction of trades whose `trade_net_return` is greater than zero.

#### Purpose

- Keep win-rate semantics aligned with the return-based trade log.
- Prevent metric code from treating the trade log like a dollar PnL ledger.

#### Canonical owner

- `src/alphaforge/metrics.py` is the authoritative owner of the win-rate formula.
- `src/alphaforge/backtest.py` is the authoritative owner of the return-based trade-log fields that supply the input.
- `src/alphaforge/report.py` and `src/alphaforge/storage.py` are downstream consumers of the computed win rate only.

#### Allowed responsibilities

- `metrics.py` MAY compute `win_rate = count(trade_net_return > 0) / trade_count`.
- `metrics.py` MAY return `0.0` when `trade_count` is zero.
- `metrics.py` MAY ignore trades whose `trade_net_return` is zero or negative when counting wins.

#### Explicit non-responsibilities

- `metrics.py` MUST NOT compute win rate from dollar PnL labels.
- `metrics.py` MUST NOT rely on shares-level accounting or quantity-based profit reconstruction to determine win rate.
- `report.py` and `storage.py` MUST NOT redefine the win-rate formula locally.

#### Inputs / outputs / contracts

- Inputs:
  - the canonical return-based trade log
  - `trade_count`
- Output:
  - `win_rate`
- Contract rules:
  - the trade log field `trade_net_return` is the authoritative input for win counting
  - the win-rate rule is independent of any PnL-style legacy label that may exist in older artifacts

#### Invariants

- Positive return counts as a win.
- Zero or negative return does not count as a win.
- No-trade results return `0.0`.

#### Cross-module dependencies

- `backtest.py` provides the canonical return-based trade data.
- `report.py` may display the resulting metric, but it must not reinterpret it as a dollar accounting statistic.
- `storage.py` may serialize the metric, but it must not recalculate it from a different field.

#### Failure modes if this boundary is violated

- Different modules can disagree on what a "winning" trade is.
- A PnL-shaped legacy field can silently become the metric source of truth.
- Report summaries can diverge from metrics computations when they relabel the same trade contribution differently.

#### Migration notes from current implementation

- The current win-rate implementation already counts positive trade outcomes.
- This change makes the return-based input field and the formula explicit so the new trade-log schema and the metric formula stay aligned.

#### Open questions / deferred decisions

- None for the win-rate formula.

#### Scenario: return-based trade log yields the expected win rate

- GIVEN a trade log with three trades and `trade_net_return` values of `0.03`, `0.00`, and `-0.01`
- WHEN `metrics.py` computes win rate
- THEN the result SHALL be `1 / 3`
- AND the zero-return trade SHALL not count as a win

