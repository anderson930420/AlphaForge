# artifact-schema-and-output-layout Specification

## Purpose
Define the canonical persisted artifact schema and output layout for AlphaForge workflows, including single-run, search, validation, walk-forward, and diagnostic artifacts.
## Requirements
### Requirement: `storage.py` is the canonical owner of persisted artifact schema and output layout

`src/alphaforge/storage.py` SHALL own the persisted artifact schema, filename, and output layout for the research validation protocol summary artifact.

The research validation protocol workflow SHALL persist a top-level `research_protocol_summary.json` artifact under `output_dir / experiment_name` when persistence is requested.

#### Scenario: research protocol summary uses storage-owned filename and payload

- GIVEN the research validation protocol workflow is run with an output directory and experiment name
- WHEN the workflow persists its protocol summary
- THEN storage MUST write `research_protocol_summary.json` under the workflow root
- AND storage MUST define the JSON payload fields for development evidence, walk-forward evidence, optional permutation evidence, frozen plan, final holdout result, transaction cost assumptions, row counts, periods, and artifact references
- AND CLI and runner code MUST consume storage-owned receipt paths rather than hardcoding a separate persisted schema

#### Scenario: protocol summary artifact does not redefine lower-level artifact schemas

- GIVEN the research protocol summary references development search, walk-forward, permutation, or final holdout artifacts
- WHEN storage serializes the protocol summary
- THEN those nested references MUST remain references or serialized summaries derived from existing runtime/storage contracts
- AND the protocol summary MUST NOT redefine single-run, search, validation, walk-forward, or permutation artifact schemas

### Requirement: Runtime dataclasses are not the persisted artifact schema owner

`src/alphaforge/schemas.py` SHALL remain the authoritative owner of in-memory runtime contracts, while `storage.py` SHALL own the persisted schema emitted from those contracts.

#### Purpose

- Keep runtime truth separate from on-disk truth.
- Prevent field overlap from making dataclasses accidental persistence owners.

#### Canonical owner

- `src/alphaforge/schemas.py` is the authoritative owner of runtime dataclasses and runtime-only result semantics.
- `src/alphaforge/storage.py` is the authoritative owner of persisted schemas and write-time conversion rules.
- Any serializer adjacent to storage is storage-owned and not a second owner.

#### Allowed responsibilities

- `schemas.py` MAY define runtime dataclasses, typed containers, and in-memory fields that are meaningful before anything is written.
- `storage.py` MAY define storage serializers, JSON/CSV field shapes, and write-time layout rules derived from runtime objects.
- `storage.py` MAY attach persistence-reference fields to receipts or persisted summaries when those fields identify already-materialized artifacts.

#### Explicit non-responsibilities

- `schemas.py` MUST NOT own output directory layout, filename generation, JSON/CSV ordering, or write-time file path materialization.
- `storage.py` MUST NOT redefine runtime meaning such as metric formulas, execution semantics, or workflow semantics.
- Runtime dataclasses MUST NOT be treated as the authoritative persisted schema just because `asdict()` or similar helpers can serialize them.

#### Inputs / outputs / contracts

- Runtime contract scope:
  - `ExperimentResult`
  - `ValidationResult`
  - `WalkForwardFoldResult`
  - `WalkForwardResult`
  - runtime metadata meaningful before persistence
- Persistence contract scope:
  - JSON summaries and CSV exports written by storage
  - storage-owned path receipts
  - path fields that identify already-materialized artifacts
- Serialization boundary:
  - runtime object in
  - storage-owned serializer converts it
  - persisted payload out
  - the resulting persisted schema is authoritative only because storage emitted it

#### Invariants

- Overlapping field names do not make runtime and persisted contracts identical.
- Runtime objects remain valid even before persistence has occurred.
- Storage may return persisted references, but those references do not redefine runtime meaning.
- If a field exists only for storage bookkeeping, it must not be promoted into runtime truth by accident.

#### Cross-module dependencies

- `experiment_runner.py` consumes runtime result objects and requests persistence when needed.
- `cli.py` may display persisted paths, but only as downstream references.
- `report.py` may consume runtime result objects and persisted artifact refs to render output.
- `README.md`, `PROJECT_BRIEF.md`, and docstrings are derived and must not become the only place a persisted schema is defined.

#### Failure modes if this boundary is violated

- Runtime result objects accumulate file-path fields and start to depend on storage side effects.
- Serializer helpers diverge from the runtime dataclasses and create incompatible JSON/CSV payloads.
- Callers begin to rely on `asdict()` output instead of the storage-owned persisted schema.
- Changing a storage filename accidentally becomes a runtime-contract breaking change.

#### Migration notes from current implementation

- `schemas.py` already contains runtime dataclasses that are separate from storage serializers.
- `storage.py` already converts runtime objects into JSON/CSV payloads and materializes receipts.
- Some path references still travel through runtime-facing result objects during workflow execution, which makes the boundary easy to blur in callers.
- This requirement formalizes the separation so runtime consumers know what is in-memory truth and what is storage truth.

#### Open questions / deferred decisions

- Whether future persistence receipts should be represented by separate storage-owned dataclasses instead of attachment fields on runtime results is deferred.
  - Recommended default: keep runtime objects runtime-only and add separate storage-owned receipts when a new persistence concern needs a richer contract.

#### Scenario: persisted schema is storage-owned even when runtime fields overlap

- GIVEN a runtime dataclass shares names with fields emitted to JSON or CSV
- WHEN storage writes the persisted artifact
- THEN storage SHALL own the output field order and layout
- AND runtime objects SHALL remain valid even if their serialized shape differs from the persisted contract

### Requirement: Artifact references are split between canonical storage facts and derived presentation refs

`storage.py` SHALL own canonical artifact path references, while report and CLI layers SHALL treat report links and presentation paths as derived references only.

#### Purpose

- Keep storage facts stable while allowing presentation layers to link to them explicitly.
- Prevent report links or CLI payloads from becoming a second persistence source of truth.

#### Canonical owner

- `src/alphaforge/storage.py` is the authoritative owner of canonical artifact path facts.
- `src/alphaforge/report.py`, `src/alphaforge/search_reporting.py`, `src/alphaforge/cli.py`, and `src/alphaforge/experiment_runner.py` may surface derived presentation refs, but they do not own the path truth.

#### Allowed responsibilities

- `storage.py` MAY return canonical path references for written artifacts.
- `storage.py` MAY expose optional report-related presentation refs when they are explicitly produced alongside persisted outputs.
- `report.py` and `search_reporting.py` MAY render relative links from explicit base directories and explicit artifact refs.
- `cli.py` MAY print derived refs such as `report_path`, `search_report_path`, or `validation_summary_path` when those refs already exist.

#### Explicit non-responsibilities

- `report.py` and `search_reporting.py` MUST NOT infer storage layout from hidden path guesses when explicit refs are available.
- `cli.py` MUST NOT reinterpret presentation refs as persistence truth.
- `experiment_runner.py` MUST NOT invent path conventions to simplify orchestration payloads.
- Optional presentation refs MUST NOT be promoted into canonical persisted artifact schema unless storage explicitly owns them.

#### Inputs / outputs / contracts

- Canonical storage facts:
  - `run_dir`
  - `equity_curve_path`
  - `trade_log_path`
  - `metrics_summary_path`
  - `ranked_results_path`
  - `train_ranked_results_path`
  - `validation_summary_path`
  - `walk_forward_summary_path`
  - `fold_results_path`
- Derived presentation refs:
  - `report_path`
  - `best_report_path`
  - `comparison_report_path`
  - `search_report_path`
- Contract rules:
  - storage-owned facts identify already-materialized artifacts
  - presentation refs are convenience links or display outputs derived from those facts
  - relative links may be rendered only from an explicit link base and explicit artifact references

#### Invariants

- A presentation ref never replaces a canonical storage path.
- The same artifact may be displayed through CLI, report HTML, or search comparison HTML, but the underlying path truth remains storage-owned.
- Relative links are stable only relative to the explicit base directory supplied to the report layer.
- If a presentation ref is absent, downstream consumers must treat it as optional and not infer a missing canonical artifact.

#### Cross-module dependencies

- `report.py` uses artifact refs to render hyperlinks.
- `search_reporting.py` uses receipts and report refs to build search comparisons.
- `cli.py` forwards or prints derived refs for user convenience.
- `experiment_runner.py` passes through storage-owned receipts and derived presentation refs without redefining them.

#### Failure modes if this boundary is violated

- Best-report links drift because report code guesses a different relative base than the storage contract.
- CLI payloads imply a report exists at a path that was never materialized.
- Report HTML starts depending on ad hoc directory structure instead of explicit storage refs.
- Storage receipts become polluted with display-only semantics and stop being clean persistence contracts.

#### Migration notes from current implementation

- `ArtifactReceipt` already distinguishes canonical persisted paths from optional presentation refs for search reports.
- `cli.py` currently surfaces `report_path` and `search_report_path` as presentation refs in JSON output.
- `report.py` and `search_reporting.py` already render links from explicit path inputs, but they also carry local filename knowledge.
- The current implementation is close to the intended split, but the path authority still needs to be stated explicitly so later changes do not recreate hidden truth.

#### Open questions / deferred decisions

- Whether single-run `report_path` should eventually move into a storage-owned receipt field or remain a CLI/report presentation ref is deferred.
  - Recommended default: keep it as a derived presentation ref unless storage starts to own a richer report-artifact receipt.

#### Scenario: report links are rendered from explicit storage facts

- GIVEN a search comparison report is rendered
- WHEN the renderer needs links to run artifacts and the best report
- THEN it SHALL use explicit artifact refs and the explicit link base only
- AND it SHALL NOT infer path targets from hidden directory layout assumptions

