# Design: integrate-permutation-evidence-into-validation-workflow

## Decision

Extend the existing validation orchestration with an optional permutation diagnostic step that runs after candidate selection and the test rerun.

The workflow remains:

1. train-side search
2. select best candidate
3. rerun selected candidate on the test split
4. optionally run permutation diagnostics on the selected candidate’s test window
5. evaluate research policy with the resulting permutation summary when available
6. persist validation and permutation artifacts

## Data contracts

### Validation permutation config

Add a small config object to carry CLI intent through the workflow:

- `enabled: bool`
- `permutations: int`
- `seed: int`
- `block_size: int`
- `null_model: str`
- `scope: str = "test"`

### Validation evidence

The validation evidence object SHALL be able to carry:

- the permutation summary, when produced
- the permutation diagnostic status, so a skipped opt-out is distinct from a successful permutation run
- artifact references for the permutation summary and score CSV

### Validation artifact receipt

Persisted validation receipts SHALL include the permutation artifact paths when the diagnostic runs.

## Execution rules

- The permutation diagnostic runs only after the selected candidate is known.
- The diagnostic uses the selected strategy family and its exact selected parameters.
- The diagnostic runs on the test evaluation window only.
- If the diagnostic is disabled, validation explicitly records that it was skipped by opt-out.
- If the diagnostic is enabled but unavailable, the workflow still reaches research policy with a missing summary so the policy can reject/degrade under existing semantics.

## Research policy integration

- When permutation diagnostics are enabled and successful, pass the real summary into `research_policy.py`.
- Do not force `max_permutation_p_value=None` as a workaround when evidence is available.
- When diagnostics are disabled, preserve the existing opt-out behavior so current callers do not change unless they opt in.

## Persistence

- Persist `permutation_test_summary.json` and `permutation_scores.csv` under the validation output directory when diagnostics run.
- Reuse the existing permutation-test serialization layout so validation and standalone outputs stay compatible.

## Reporting

- Validation summary output SHALL expose:
  - permutation diagnostic status
  - null model
  - permutation count
  - seed
  - block size
  - empirical p-value
  - real observed metric / score
  - research policy decision
- The report layer should render already-produced evidence only; it should not recompute diagnostics.

## Out of scope

- GA
- ML/DL
- broker APIs
- new strategy families
- redesigning the runner
- broad permutation algorithm changes
