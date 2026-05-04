# Delta for Candidate Validation and Evidence Contract

## ADDED Requirements

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

