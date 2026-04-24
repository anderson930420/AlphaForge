# Delta for Validation Permutation Evidence Status Semantics

## ADDED Requirements

### Requirement: validation permutation status separates execution from policy outcome

AlphaForge SHALL report validation permutation status using explicit execution-oriented values.

#### Purpose

- Distinguish a successful diagnostic that failed the p-value threshold from an execution error.
- Keep research policy rejection semantics separate from diagnostic completion semantics.

#### Canonical owner

- `src/alphaforge/runner_workflows.py` classifies validation permutation status.
- `src/alphaforge/schemas.py` defines the validation evidence contract.

#### Scenario: skipped by explicit opt-out

- GIVEN validation permutation testing is not requested
- WHEN validation evidence is serialized
- THEN the permutation status SHALL be `skipped`

#### Scenario: completed and passed

- GIVEN permutation diagnostics complete and the empirical p-value is within threshold
- WHEN validation evidence is serialized
- THEN the permutation status SHALL be `completed_passed`

#### Scenario: completed but failed threshold

- GIVEN permutation diagnostics complete and the empirical p-value exceeds the configured threshold
- WHEN validation evidence is serialized
- THEN the permutation status SHALL be `completed_failed`
- AND the research policy decision SHALL still reject the candidate under the configured threshold

#### Scenario: diagnostic error

- GIVEN permutation diagnostics are enabled but the diagnostic cannot produce usable evidence
- WHEN validation evidence is serialized
- THEN the permutation status SHALL be `error`
- AND the research policy decision SHALL continue to reject or degrade according to existing policy semantics
