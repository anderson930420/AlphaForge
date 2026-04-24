# Delta for Validation Permutation Evidence Integration

## ADDED Requirements

### Requirement: validate-search can optionally run permutation diagnostics for the selected candidate

AlphaForge SHALL allow `validate-search` to optionally run a permutation diagnostic after the selected candidate has been chosen and rerun on the test split.

#### Purpose

- Connect the selected validation candidate to a real permutation summary instead of intentionally opting out of p-value enforcement.
- Keep validation diagnostics aligned with the actual out-of-sample candidate that will be judged by research policy.

#### Canonical owner

- `src/alphaforge/runner_workflows.py` coordinates the workflow.
- `src/alphaforge/permutation.py` owns permutation execution semantics.

#### Scenario: diagnostic is disabled by default

- GIVEN `validate-search` is invoked without `--permutation-test`
- WHEN the validation workflow runs
- THEN the workflow SHALL preserve the existing opt-out behavior
- AND validation SHALL record that permutation evidence was skipped by user intent

#### Scenario: diagnostic runs only after candidate selection

- GIVEN `validate-search` selects a best candidate from train-search results
- WHEN permutation diagnostics are enabled
- THEN the permutation diagnostic SHALL use the selected candidate’s actual strategy family and parameters
- AND the diagnostic SHALL run after the selected candidate is known

#### Scenario: diagnostic runs on the test evaluation window

- GIVEN a selected validation candidate and its test split
- WHEN permutation diagnostics are enabled
- THEN the diagnostic SHALL use the test evaluation window only
- AND it SHALL NOT influence train-side candidate selection

### Requirement: permutation evidence is passed into research policy when available

AlphaForge SHALL pass the real permutation summary into `research_policy.py` when permutation diagnostics are enabled and successful.

#### Purpose

- Allow permutation p-value enforcement to operate on real evidence.
- Avoid bypassing permutation p-value checks with `None` when evidence exists.

#### Canonical owner

- `src/alphaforge/research_policy.py` owns the policy decision.

#### Scenario: successful permutation evidence reaches policy

- GIVEN permutation diagnostics produced a summary
- WHEN research policy evaluation runs
- THEN the real summary SHALL be passed to the policy evaluator
- AND the policy SHALL evaluate p-value enforcement using the configured threshold

#### Scenario: missing evidence is not silently suppressed

- GIVEN permutation diagnostics are enabled but no summary is available
- WHEN research policy evaluation runs
- THEN the policy SHALL not be bypassed by forcing `max_permutation_p_value=None`
- AND the validation summary SHALL expose that the permutation evidence was unavailable

### Requirement: validation summaries persist permutation artifacts and expose their status

AlphaForge SHALL persist permutation diagnostic artifacts under the validation output directory and SHALL expose the diagnostic status in validation outputs.

#### Purpose

- Make permutation diagnostics auditable alongside validation artifacts.
- Distinguish skipped opt-out from a successful permutation run.

#### Canonical owner

- `src/alphaforge/storage.py` owns persisted artifact references.
- `src/alphaforge/schemas.py` owns the evidence/result contracts.

#### Scenario: permutation artifacts are persisted

- GIVEN permutation diagnostics are enabled for validation
- WHEN validation artifacts are written
- THEN `permutation_test_summary.json` SHALL be written
- AND `permutation_scores.csv` SHALL be written
- AND validation outputs SHALL reference those artifacts

#### Scenario: validation summary exposes permutation state

- GIVEN validation ran with permutation diagnostics enabled or explicitly skipped
- WHEN the validation summary is serialized
- THEN the summary SHALL expose whether permutation evidence was run and passed, run and failed, skipped by opt-out, or unavailable

