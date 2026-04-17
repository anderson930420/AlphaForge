# Delta for Candidate Promotion and Rejection Policy

## ADDED Requirements

### Requirement: validation and walk-forward flows expose explicit policy decisions

`validate-search` and `walk-forward` SHALL emit explicit policy decisions for searched candidates instead of leaving verdict meaning implicit inside evidence summaries.

#### Purpose

- Distinguish “evidence exists” from “the current policy accepts or rejects the candidate.”
- Keep policy evaluation separate from evidence assembly, storage, and presentation.

#### Canonical owner

- `src/alphaforge/policy.py` is the authoritative owner of the post-search candidate promotion/rejection policy.
- `src/alphaforge/schemas.py` is the authoritative owner of the runtime policy-decision contract.
- `src/alphaforge/experiment_runner.py` is the authoritative owner of wiring evidence into the policy evaluator.
- `src/alphaforge/storage.py` is the authoritative owner of serializing policy decisions into validation and walk-forward artifacts.

#### Policy inputs

- validation policy inputs:
  - candidate evidence summary
  - train metrics
  - test metrics
  - benchmark-relative summary
  - degradation summary
- walk-forward policy inputs:
  - aggregate walk-forward evidence summary
  - fold counts
  - aggregate test metrics
  - aggregate benchmark metrics

#### Policy outputs

- policy name
- policy scope
- final verdict
- decision reasons

#### Policy scope

- The same policy family applies to both `validate-search` and `walk-forward`.
- Validation outputs SHALL carry a validation-scoped decision.
- Walk-forward outputs SHALL carry a walk-forward-scoped decision.

#### Verdict semantics

- `validated` is used only when evidence is complete and meets the policy’s pass conditions.
- `rejected` is used only when evidence is complete and clearly fails the policy’s reject conditions.
- `inconclusive` is used when evidence is missing, incomplete, skipped, or mixed.

#### Scenario: validation emits a policy decision

- GIVEN a searched candidate has train/test evidence
- WHEN `validate-search` completes
- THEN the result SHALL include a policy decision with a verdict and decision reasons
- AND report/presentation layers SHALL not infer the verdict on their own

#### Scenario: walk-forward emits a policy decision

- GIVEN walk-forward returns fold-level evidence and aggregate evidence
- WHEN the walk-forward workflow completes
- THEN the result SHALL include a walk-forward policy decision with a verdict and decision reasons
- AND the verdict SHALL be derived from the aggregate evidence, not guessed from presentation data
