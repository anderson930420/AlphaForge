# Design: stabilize-cli-output-and-artifact-discovery

## Canonical ownership mapping

- `src/alphaforge/cli.py` will remain the sole owner of the command-facing JSON payload shape for `run`, `search`, `validate-search`, and `walk-forward`.
- `src/alphaforge/storage.py` will remain the sole owner of canonical persisted artifact refs and file naming.
- `src/alphaforge/report.py` and `src/alphaforge/search_reporting.py` will remain the sole owners of optional presentation/report refs.
- `src/alphaforge/experiment_runner.py` will continue to produce explicit workflow outputs, but it will not become the owner of CLI wording or payload structure.

## Contract migration plan

- Keep the existing single-run `artifacts` receipt contract and existing search summary fields stable.
- Keep the existing walk-forward summary fields stable.
- Add an explicit validation summary discovery ref to the CLI-facing validation payload so users no longer need to infer where `validation_summary.json` was written.
- Preserve the distinction between canonical persisted refs and optional report/presentation refs in the CLI payload.
- If validation needs a thin explicit discovery output from orchestration to supply the persisted summary path, that output MUST remain orchestration-only and MUST NOT alter runtime or persistence ownership.

## Duplicate logic removal plan

- Remove any CLI-local inference for validation summary discovery if it exists or is introduced during migration.
- Keep report path propagation delegated to report owners rather than reconstructing report layout in CLI.
- Keep search output field names stable; do not introduce a new search manifest or a parallel search result schema.
- Keep single-run receipt serialization storage-owned, with CLI only forwarding the receipt payload.

## Verification plan

- Add or update CLI tests for:
  - single-run output and optional report path behavior,
  - ranked-search output and optional report path behavior,
  - validate-search output including the explicit validation summary path,
  - walk-forward output including the persisted summary and fold-results paths.
- Add contract-focused assertions that required canonical refs are present and optional presentation refs are omitted when no report is generated.
- Update README examples or output notes only where they describe the stable CLI-facing keys.

## Temporary migration states

- If validation summary discovery must be threaded through a new thin runner-local output bundle, the bundle is temporary compatibility plumbing only.
- During migration, any duplicated path knowledge outside the canonical owner is advisory only and must be removed once the CLI tests pass with explicit refs.
