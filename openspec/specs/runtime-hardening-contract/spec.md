# runtime-hardening-contract Specification

## Purpose
TBD - created by archiving change harden-bar-count-and-twse-ssl-fallback. Update Purpose after archive.
## Requirements
### Requirement: MetricReport bar_count is a required positive runtime contract

AlphaForge SHALL require `MetricReport.bar_count` to be a positive integer.

#### Purpose

- Prevent invalid metric objects from silently falling through scoring semantics.
- Keep turnover normalization anchored to backtest length rather than a fallback constant.

#### Canonical owner

- `src/alphaforge/schemas.py` defines the runtime contract.
- `src/alphaforge/metrics.py` constructs valid metric reports.
- `src/alphaforge/scoring.py` consumes the contract.

#### Scenario: missing bar_count is rejected by construction

- GIVEN code constructs a `MetricReport` without `bar_count`
- WHEN the constructor runs
- THEN construction SHALL fail with `TypeError`

#### Scenario: non-positive bar_count is rejected

- GIVEN code constructs or provides a `MetricReport` with `bar_count <= 0`
- WHEN the metric report is validated or consumed for scoring
- THEN the runtime SHALL reject it with a clear error

### Requirement: scoring fails fast on invalid bar_count

AlphaForge SHALL fail fast in `scoring.py` when `MetricReport.bar_count` is invalid.

#### Purpose

- Prevent invalid metrics from silently reverting to cumulative turnover behavior.

#### Canonical owner

- `src/alphaforge/scoring.py`

#### Scenario: invalid bar_count is not normalized away

- GIVEN `score_metrics()` receives a metric report with `bar_count <= 0`
- WHEN scoring is evaluated
- THEN scoring SHALL raise a `ValueError`

### Requirement: TWSE SSL fallback logs and suppresses warnings locally only

AlphaForge SHALL keep TWSE SSL verification enabled on the normal request path and SHALL scope insecure warning suppression to the fallback retry only.

#### Purpose

- Preserve secure defaults.
- Make insecure fallback behavior auditable without silencing warnings globally.

#### Canonical owner

- `src/alphaforge/twse_client.py`

#### Scenario: normal request path stays verified

- GIVEN a TWSE request succeeds under normal SSL verification
- WHEN the client performs the request
- THEN the request SHALL not use `verify=False`

#### Scenario: SSL fallback logs and suppresses warnings locally

- GIVEN the initial TWSE request raises `requests.exceptions.SSLError`
- WHEN the client retries with insecure verification
- THEN the client SHALL log a warning about the insecure fallback
- AND the client SHALL suppress `InsecureRequestWarning` only inside the retry block
- AND the client SHALL not globally disable warnings

### Requirement: walk-forward mean_test_sharpe_ratio is descriptive only

AlphaForge SHALL treat walk-forward `mean_test_sharpe_ratio` as descriptive fold-average output only.

#### Purpose

- Prevent the arithmetic mean Sharpe output from being mistaken for a pooled decision-grade statistic.

#### Canonical owner

- `src/alphaforge/walk_forward_aggregation.py` owns the descriptive aggregate output.
- `src/alphaforge/policy.py` owns walk-forward promotion/rejection decisions.

#### Scenario: mean Sharpe is not a decision-grade statistic

- GIVEN walk-forward aggregation emits `mean_test_sharpe_ratio`
- WHEN policy decisions are evaluated
- THEN `mean_test_sharpe_ratio` SHALL be treated as descriptive only
- AND walk-forward Sharpe-based promotion or rejection SHALL rely on `pooled_test_sharpe_ratio` when available

