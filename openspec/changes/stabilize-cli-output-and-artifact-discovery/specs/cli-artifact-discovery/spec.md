# cli-artifact-discovery Specification

## ADDED Requirements

### Requirement: CLI artifact discovery has explicit workflow-scoped refs

CLI-facing artifact discovery SHALL expose canonical persisted refs and optional presentation refs explicitly for each workflow command. Users and downstream tooling SHALL be able to rely on the documented payload keys without reconstructing file locations from hidden layout rules.

#### Purpose

- Define the CLI-facing artifact discovery contract for AlphaForge so users can reliably find canonical persisted outputs and optional presentation outputs without inferring internal layout or reading implementation details.
- Freeze which artifact refs are surfaced by each workflow command and which of those refs are canonical persisted artifacts versus optional report/presentation artifacts.
- Keep `cli.py` downstream of runtime, orchestration, persistence, and presentation owners while still providing a stable user-facing discovery surface.

#### Canonical owner

- `src/alphaforge/cli.py` is the single authoritative owner of the CLI-facing artifact discovery contract.
- `src/alphaforge/storage.py` remains the canonical owner of persisted artifact refs, filenames, and directory layout.
- `src/alphaforge/report.py` and `src/alphaforge/search_reporting.py` remain the canonical owners of report/presentation artifact refs only.
- `src/alphaforge/experiment_runner.py` and runner helper modules remain orchestration-only producers of the values that the CLI surfaces.

#### Allowed responsibilities

- `cli.py` MAY:
  - assemble command-facing JSON payloads that surface artifact refs returned by orchestration, storage, or report owners,
  - include required canonical persisted artifact refs for the successful workflow,
  - include optional report/presentation refs when a workflow generates them,
  - preserve stable payload key names across releases unless this spec explicitly changes a key.
- `cli.py` MAY NOT:
  - infer artifact locations from ad hoc directory-layout logic when explicit refs exist,
  - redefine persisted filenames or report filenames,
  - recompute runtime, benchmark, or persistence semantics,
  - turn CLI output into a parallel source of truth for storage or report ownership.

#### Explicit non-responsibilities

- `cli.py` MUST NOT own runtime result schemas, execution semantics, metric formulas, benchmark formulas, or persistence contracts.
- `cli.py` MUST NOT decide report HTML content or figure content.
- `cli.py` MUST NOT invent new artifact paths that are not produced or derived from canonical owners.
- `cli.py` MUST NOT require users or downstream tooling to reconstruct canonical artifact locations from hidden layout rules.

#### Inputs / outputs / contracts

### Inputs

- Runtime results and execution bundles from `experiment_runner.py`
- Storage-owned artifact refs and serializers from `storage.py`
- Presentation/report paths returned by `report.py` or `search_reporting.py`
- CLI command arguments such as `--output-dir`, `--experiment-name`, and `--generate-report`

### Outputs

#### Single experiment run

- Stable payload keys:
  - `artifacts`
  - `report_path` when report generation is requested and a report file is created
- `artifacts` SHALL contain the storage-owned persisted refs surfaced by the single-run receipt:
  - `run_dir`
  - `equity_curve_path`
  - `trade_log_path`
  - `metrics_summary_path`
- `report_path` SHALL be treated as an optional presentation ref, not a canonical persisted experiment artifact.

#### Ranked search run

- Stable payload keys:
  - `result_count`
  - `best_result`
  - `top_results`
  - `ranked_results_path`
  - `report_path` when the best report is generated
  - `search_report_path` when the comparison report is generated
- `ranked_results_path` SHALL be treated as the canonical persisted search-result ref.
- `report_path` and `search_report_path` SHALL be treated as optional presentation refs.

#### Validation run

- Stable payload keys:
  - `validation_summary_path`
  - `train_ranked_results_path`
- `validation_summary_path` SHALL be treated as the canonical persisted validation-summary ref.
- `train_ranked_results_path` SHALL be treated as a canonical persisted ranked-training ref.

#### Walk-forward run

- Stable payload keys:
  - `walk_forward_summary_path`
  - `fold_results_path`
- Both keys SHALL be treated as canonical persisted refs.

### Contract rules

- If a workflow persists a canonical artifact, the CLI payload MUST expose that artifact through an explicit field rather than requiring reconstruction from internal directory layout.
- If a workflow generates a report HTML file, the CLI payload MUST mark it as optional presentation output rather than canonical persisted experiment output.
- If a workflow has no report HTML output, the CLI payload MUST NOT invent one.
- CLI output wording and key names for the above fields MUST remain stable enough for downstream scripts and docs to rely on them.

#### Invariants

- CLI artifact discovery is always downstream of frozen runtime, orchestration, persistence, and presentation owners.
- Presentation refs may appear in CLI output, but they do not become canonical persisted experiment artifacts.
- Canonical persisted artifact refs must be explicit enough that users can locate outputs without inferring file names from hidden layout rules.
- The same canonical ref must not be redefined with a different meaning by another module.
- Any key present in the CLI artifact-discovery contract must have a single authoritative source of truth upstream.

#### Cross-module dependencies

- `experiment_runner.py` is the orchestration source for workflow outputs passed to the CLI.
- `storage.py` is the authoritative source for persisted artifact refs and filenames.
- `report.py` and `search_reporting.py` are the authoritative sources for optional report/presentation refs.
- `README.md` and CLI tests document and verify the stable payload keys, but they are not authoritative owners of the contract.

#### Failure modes if this boundary is violated

- Users must inspect implementation details or output directory trees to find artifacts after a successful CLI command.
- Validation outputs omit the canonical summary path, forcing users to infer where the summary JSON was written.
- Report HTML outputs are mistaken for canonical persisted experiment artifacts.
- CLI payloads drift between workflows, making documentation and downstream tooling unreliable.
- CLI code starts inferring path layout locally instead of forwarding explicit refs from upstream owners.

#### Migration notes from current implementation

- Single-run CLI output already forwards storage-owned artifact refs through `ArtifactReceipt`; that behavior should remain the canonical pattern.
- Search CLI output already forwards `ranked_results_path`, `report_path`, and `search_report_path`; those keys should remain stable.
- Validation CLI output currently exposes `train_ranked_results_path` but does not yet surface the validation summary path explicitly; this change should add that ref.
- Walk-forward CLI output already exposes `walk_forward_summary_path` and `fold_results_path`; those keys should remain stable.
- README CLI examples currently document search output fields only; they need to be expanded to include validation and walk-forward discovery keys once the contract is implemented.

#### Open questions / deferred decisions

- Whether single-run CLI output should later surface a separate experiment-config path or continue to rely on the storage receipt's run directory and canonical file set is deferred.
- Whether validation and walk-forward outputs should later gain nested discovery objects rather than top-level path fields is deferred.
- Whether CLI output should eventually include a dedicated explicit artifact-discovery sub-object across all commands is deferred.

#### Scenario: Single-run discovery exposes the storage-owned receipt

- GIVEN a single experiment run completes successfully
- WHEN `cli.py` prints the command payload
- THEN the payload SHALL expose the storage-owned `artifacts` receipt
- AND that receipt SHALL distinguish canonical persisted refs from optional presentation refs
- AND the payload SHALL NOT require the user to reconstruct the receipt from directory layout knowledge

#### Scenario: Search discovery exposes ranked results and optional report paths

- GIVEN a ranked search completes successfully
- WHEN `cli.py` prints the command payload
- THEN the payload SHALL expose `ranked_results_path`
- AND it SHALL expose `report_path` and `search_report_path` only when those presentation artifacts were generated
- AND those report paths SHALL remain optional presentation refs

#### Scenario: Validation discovery exposes the canonical persisted summary

- GIVEN a validation run completes successfully
- WHEN `cli.py` prints the command payload
- THEN the payload SHALL expose `validation_summary_path`
- AND it SHALL expose `train_ranked_results_path`
- AND neither field SHALL be treated as a presentation/report artifact

#### Scenario: Walk-forward discovery exposes the canonical summary and fold results

- GIVEN a walk-forward run completes successfully
- WHEN `cli.py` prints the command payload
- THEN the payload SHALL expose `walk_forward_summary_path`
- AND it SHALL expose `fold_results_path`
- AND both fields SHALL remain canonical persisted refs
