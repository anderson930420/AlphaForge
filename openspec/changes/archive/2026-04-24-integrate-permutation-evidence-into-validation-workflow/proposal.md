# Proposal: integrate-permutation-evidence-into-validation-workflow

## Boundary problem

- `validate-search` already performs train-search, selects the best candidate, reruns that candidate on the test split, and evaluates research policy.
- Research policy now defaults to enforcing permutation p-values, but validation still intentionally opts out because no permutation summary is generated in the workflow.
- This leaves the validation pipeline incomplete: the selected candidate is rerun, but the out-of-sample decision is not paired with permutation evidence.

## Canonical ownership decision

- `src/alphaforge/runner_workflows.py` coordinates the validation workflow and may invoke permutation diagnostics after candidate selection.
- `src/alphaforge/permutation.py` owns permutation/null-model construction and permutation-test execution semantics.
- `src/alphaforge/research_policy.py` owns promotion/rejection decisions and consumes the permutation summary when available.
- `src/alphaforge/schemas.py` owns runtime evidence/result contracts.
- `src/alphaforge/storage.py` owns persisted artifact paths and validation summary serialization.
- `src/alphaforge/cli.py` exposes user intent through flags; it does not compute research statistics.

## Scope

- Add optional permutation diagnostics to `validate-search`.
- Run the diagnostic only after the selected candidate is chosen and the test rerun is available.
- Pass the selected candidate’s actual strategy family and parameters into permutation execution.
- Default to test-window permutation diagnostics for the selected candidate only.
- Persist permutation summary and score artifacts under the validation output directory.
- Carry permutation summary and status through validation evidence and validation summary output.
- Expose CLI flags for enabling the diagnostic and configuring the permutation run.

## Explicitly out of scope

- GA
- ML/DL
- broker APIs
- new strategy families
- redesigning the runner
- rewriting permutation algorithms
- changing standalone permutation-test behavior beyond minimal sharing

## Migration risk

- Validation summaries will gain additional permutation fields and artifact references.
- Existing validate-search callers that do not opt in will continue to behave as before, including explicit p-value opt-out behavior.
- New CLI flags must not change default validation behavior unless `--permutation-test` is provided.

## Acceptance conditions

- OpenSpec validates for `integrate-permutation-evidence-into-validation-workflow`.
- `validate-search` can produce and persist a permutation summary for the selected candidate.
- Research policy receives the real permutation summary when the diagnostic is enabled.
- Validation summaries expose permutation status, summary data, and artifact references.
- Full pytest passes.
