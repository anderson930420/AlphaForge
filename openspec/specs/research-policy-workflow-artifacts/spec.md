# research-policy-workflow-artifacts Specification

## Purpose
TBD - created by archiving change integrate-research-policy-workflow-artifacts. Update Purpose after archive.
## Requirements
### Requirement: validate-search persists an explicit research-policy decision artifact

When `validate-search` assembles candidate evidence, the workflow SHALL evaluate a research-policy decision using the existing pure policy layer and SHALL persist the decision as a JSON artifact.

The persisted decision SHALL include:

- `candidate_id`
- `verdict`
- `reasons`
- `checks`
- `max_reruns`
- `rerun_count`
- a simple policy-config snapshot when available

The workflow output SHALL expose the policy artifact path through its persisted artifact receipt and serialized summary payload.

The policy decision SHALL be advisory in this slice and SHALL NOT replace the existing validation verdict or prevent artifact generation.

#### Scenario: validate-search exposes a default passing policy decision

- GIVEN a validation run whose candidate evidence satisfies the configured research policy checks
- WHEN the workflow completes
- THEN the workflow output SHALL include a research-policy decision
- AND the verdict SHALL be `promote`
- AND the persisted validation artifact receipt SHALL include a `policy_decision_path`
- AND the persisted JSON artifact SHALL contain the policy decision fields

#### Scenario: configured trade-count guardrail rejects weak candidates

- GIVEN a validation run with a candidate evidence trade count below the configured minimum
- AND a research-policy config that requires a higher minimum trade count
- WHEN the workflow completes
- THEN the research-policy decision verdict SHALL be `reject`
- AND the persisted decision SHALL include human-readable reasons and check results

#### Scenario: existing validation behavior remains unchanged

- GIVEN a normal validation run without explicit research-policy configuration
- WHEN the workflow completes
- THEN the validation result SHALL continue to expose the existing validation verdict
- AND the workflow SHALL still persist the research-policy decision artifact
- AND the additional artifact SHALL be additive rather than blocking

