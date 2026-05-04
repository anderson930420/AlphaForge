# candidate-validation-and-evidence-contract Specification

## Purpose
Define the canonical candidate-evidence contract for `validate-search` and walk-forward fold outputs, including evidence summaries, degradation semantics, and fold/aggregate evidence relationships.
## Requirements
### Requirement: validation flows expose a canonical candidate-evidence summary

`validate-search` SHALL produce a canonical candidate-evidence summary for the searched candidate it evaluates on the train/test split.

#### Degradation semantics

- return degradation SHALL be calculated as `test_annualized_return - train_annualized_return`
- `return_degradation` SHALL mean period-normalized return degradation, not raw total-return degradation
- annualized return values SHALL come from `MetricReport.annualized_return`, whose formula is owned by `src/alphaforge/metrics.py`
- Sharpe degradation SHALL be calculated as `test_sharpe_ratio - train_sharpe_ratio`
- max-drawdown delta SHALL be calculated as `test_max_drawdown - train_max_drawdown`
- the degradation summary SHALL use stable field names and SHALL not invent a larger scoring system

#### Scenario: validation return degradation is period-normalized

- GIVEN a candidate has been evaluated on train and test data with unequal segment lengths
- AND the test segment has lower raw total return than the train segment
- AND the test annualized return is equal to or greater than the train annualized return
- WHEN the validation evidence summary is assembled
- THEN `return_degradation` SHALL be non-negative
- AND the validation policy SHALL NOT fail solely because test raw total return is lower than train raw total return

### Requirement: walk-forward flows expose fold-level candidate evidence and an aggregate evidence summary

`walk-forward` SHALL expose fold-level candidate evidence for each fold and a separate aggregate evidence summary for the overall walk-forward result.

#### Purpose

- Keep fold-level candidate evidence distinct from the aggregate walk-forward view.
- Avoid collapsing fold-specific selected candidates into a single misleading candidate identity.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` is the authoritative owner of assembling fold evidence and aggregate walk-forward evidence.
- `src/alphaforge.walk_forward_aggregation.py` remains the authoritative owner of aggregate metric calculations.

#### Fold-level evidence

- each fold SHALL carry its own candidate-evidence summary
- fold evidence SHALL include the same candidate-evidence fields as validation evidence whenever the fold produced a searched candidate and a test result

#### Aggregate evidence

- the walk-forward aggregate summary SHALL include:
  - fold count
  - validated fold count
  - skipped fold count
  - aggregate test metrics
  - aggregate benchmark metrics
  - verdict/status
  - artifact paths when produced
- aggregate evidence SHALL be derived from fold evidence and aggregate metrics
- aggregate evidence SHALL be required for returned walk-forward results even when no folds are valid; in that case the verdict SHALL be `inconclusive`

#### Relationship between fold and aggregate summaries

- fold summaries are the source material
- aggregate summaries summarize the fold summaries
- the aggregate summary SHALL not invent a second search rank or a second candidate identity when folds select different candidates

#### Scenario: walk-forward aggregate evidence remains explicit

- GIVEN a walk-forward run returns multiple folds
- WHEN the aggregate evidence summary is assembled
- THEN it SHALL report fold counts and aggregate metrics explicitly
- AND it SHALL not guess a single candidate identity when folds differ

### Requirement: candidate evidence includes minimal research evidence diagnostics

`CandidateEvidenceSummary` SHALL include minimal research evidence diagnostics for cost sensitivity and bootstrap evidence whenever the research-validation workflow evaluates a candidate.

#### Purpose

- Surface the smallest useful evidence signal needed before park readiness.
- Keep diagnostics attached to the existing evidence summary instead of inventing a new standalone evidence schema.

#### Canonical owner

- `src/alphaforge/evidence_diagnostics.py` SHALL be the canonical owner of the diagnostic formulas.
- `src/alphaforge/runner_workflows.py` SHALL orchestrate the diagnostics and attach the results to candidate evidence.
- `src/alphaforge/storage.py` SHALL serialize the resulting evidence fields.

#### Cost sensitivity shape

Candidate evidence SHALL include a `cost_sensitivity` object with:

- `low_cost`
- `base_cost`
- `high_cost`
- `verdict`

Each scenario entry SHALL expose at least:

- `annualized_return`
- `sharpe`
- `max_drawdown`

#### Bootstrap evidence shape

Candidate evidence SHALL include a `bootstrap_evidence` object with:

- `n_bootstrap`
- `seed`
- `annualized_return_ci_95`
- `mean_daily_return_ci_95`
- `ci_crosses_zero`
- `verdict`

An optional `sharpe_ci_95` MAY be included only when cleanly supported by the diagnostics implementation.

#### Scenario: candidate evidence carries both diagnostics

- GIVEN a candidate is evaluated through research validation
- WHEN the candidate evidence summary is assembled
- THEN it SHALL include cost sensitivity and bootstrap evidence
- AND the evidence objects SHALL be serializable into storage-owned artifacts

### Requirement: cost sensitivity verdict is evidence-only and uses existing guardrails

AlphaForge SHALL mark a candidate `cost_fragile` when the candidate only remains acceptable under `low_cost` but fails under `base_cost` or `high_cost`.

If existing research-policy guardrails are available, the verdict SHOULD be based on whether the candidate remains acceptable under those guardrails at each cost scenario. The implementation MAY use a small local rule only if the existing policy contract cannot express the decision cleanly.

#### Scenario: low-cost-only success is fragile

- GIVEN a candidate passes only under `low_cost`
- AND it fails under `base_cost` or `high_cost`
- WHEN the cost-sensitivity diagnostic is assembled
- THEN the verdict SHALL be `cost_fragile`

#### Scenario: stable candidates remain stable

- GIVEN a candidate remains acceptable under the selected research policy at all cost scenarios
- WHEN the cost-sensitivity diagnostic is assembled
- THEN the verdict SHALL be `stable`

### Requirement: bootstrap evidence uses minimal confidence intervals

AlphaForge SHALL treat bootstrap evidence as a minimal robustness diagnostic and SHALL record whether the confidence interval crosses zero.

The bootstrap evidence verdict SHALL be:

- `stronger_evidence` when the confidence interval lower bound is above zero
- `weak_evidence` when the confidence interval crosses zero

#### Scenario: CI crossing zero is weak evidence

- GIVEN the bootstrap confidence interval includes zero
- WHEN the bootstrap evidence diagnostic is assembled
- THEN `ci_crosses_zero` SHALL be true
- AND the verdict SHALL be `weak_evidence`

#### Scenario: positive CI lower bound is stronger evidence

- GIVEN the bootstrap confidence interval lower bound is greater than zero
- WHEN the bootstrap evidence diagnostic is assembled
- THEN `ci_crosses_zero` SHALL be false
- AND the verdict SHALL be `stronger_evidence`

