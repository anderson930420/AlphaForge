# Proposal: stabilize-cli-output-and-artifact-discovery

## Boundary problem

- `src/alphaforge/cli.py` already emits workflow result payloads, but the exact user-facing artifact discovery contract is still under-specified across the four workflow commands.
- Single-run output surfaces storage-owned artifact refs through `ArtifactReceipt`, but the CLI contract does not yet explicitly name which refs are canonical persisted outputs versus optional presentation refs.
- Search output already surfaces `ranked_results_path`, `report_path`, and `search_report_path`, but those fields are documented more clearly in code and tests than in an approved CLI-facing contract.
- Validation output currently exposes `train_ranked_results_path` but does not yet surface the persisted validation summary path as an explicit discovery field, so users still need to rely on command/output layout knowledge for the summary artifact.
- Walk-forward output surfaces summary and fold-results paths, but the CLI-facing discovery contract for those fields is still implicit rather than frozen as a stable user-facing rule.

## Canonical ownership decision

- `src/alphaforge/cli.py` becomes the single authoritative owner of the CLI-facing artifact discovery contract.
- `src/alphaforge/storage.py` remains the single authoritative owner of canonical persisted artifact refs and persisted filename/layout rules.
- `src/alphaforge/report.py` and `src/alphaforge/search_reporting.py` remain the authoritative owners of presentation/report artifact refs only.
- `src/alphaforge/experiment_runner.py` and runner helper modules remain orchestration-only producers of explicit refs and summaries for the CLI to surface.

## Scope

- Single experiment run payloads:
  - `artifacts`
  - `report_path` when report generation is requested
- Ranked search payloads:
  - `result_count`
  - `best_result`
  - `top_results`
  - `ranked_results_path`
  - `report_path` when the best report exists
  - `search_report_path` when the search comparison report exists
- Validation payloads:
  - `validation_summary_path`
  - `train_ranked_results_path`
- Walk-forward payloads:
  - `walk_forward_summary_path`
  - `fold_results_path`
- CLI help text, README usage notes, and focused CLI tests that describe and lock these payload fields

## Migration risk

- Adding or renaming CLI payload keys can break downstream scripts or docs that parse the current JSON output.
- Validation output currently lacks an explicit summary-path field, so surfacing that path will be a visible CLI behavior change even though the persisted artifact itself already exists.
- If CLI discovery re-infers file layout instead of consuming explicit refs, the contract will remain ambiguous and will drift again.
- If presentation refs and canonical persisted refs are not separated explicitly, users will keep mistaking report HTML files for canonical persisted experiment outputs.

## Acceptance conditions

- CLI-facing artifact discovery is explicitly documented for single-run, search, validation, and walk-forward workflows.
- Canonical persisted refs and optional presentation/report refs are clearly separated in the CLI contract.
- Validation output surfaces the persisted summary path explicitly instead of requiring layout inference.
- CLI output remains compatible except for small, documented additions needed to remove ambiguity.
- Runtime, orchestration, persistence, report, and visualization ownership boundaries remain unchanged.
- Tests prove the CLI output keys and optional-vs-required artifact refs remain stable.
