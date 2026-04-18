# artifact-schema-and-output-layout Specification

## Purpose
Define the canonical persisted artifact schema and output layout for AlphaForge workflows, including single-run, search, validation, walk-forward, and diagnostic artifacts.
## Requirements
### Requirement: `storage.py` is the canonical owner of persisted artifact schema and output layout

`src/alphaforge/storage.py` SHALL be the single authoritative owner of persisted artifact schema, artifact naming, artifact path derivation, and output directory layout for AlphaForge persisted workflow artifacts.

#### Purpose

- Freeze one persistence contract so search, validation, walk-forward, and single-run outputs all follow the same storage-owned rules.
- Prevent `experiment_runner.py`, `report.py`, `search_reporting.py`, `cli.py`, or runtime dataclasses from becoming parallel owners of filenames or directory trees.

#### Canonical owner

- `src/alphaforge/storage.py` is the only authoritative owner of:
  - persisted artifact schema,
  - artifact naming,
  - artifact filename generation,
  - output directory layout,
  - run-directory layout,
  - search-output layout,
  - validation-output layout,
  - walk-forward-output layout,
  - report file placement as a persisted artifact concern,
  - artifact path derivation rules intended to be canonical.
- `src/alphaforge/schemas.py` remains the authoritative owner of in-memory runtime contracts only.
- `src/alphaforge/experiment_runner.py`, `src/alphaforge/report.py`, `src/alphaforge/search_reporting.py`, `src/alphaforge/visualization.py`, and `src/alphaforge/cli.py` are downstream consumers only.

#### Allowed responsibilities

- `storage.py` MAY:
  - define canonical filenames,
  - define root/output directory composition rules,
  - write persisted JSON/CSV payloads,
  - construct storage-owned receipts and path references,
  - convert runtime objects into persisted artifact payloads,
  - attach optional presentation refs to receipts when the caller has already materialized them,
  - define compatibility metadata for persisted artifacts if needed later.

#### Explicit non-responsibilities

- `storage.py` MUST NOT own execution semantics, market-data acceptance, benchmark semantics, report rendering, or strategy semantics.
- `experiment_runner.py` MUST NOT own persisted artifact schema or layout rules, even when it sequences writes.
- `report.py` and `search_reporting.py` MUST NOT become canonical owners of filename or directory conventions.
- `cli.py` MUST NOT hardcode output layout as business truth.
- Runtime dataclasses and helper serializers MUST NOT become the authoritative persistence schema owner unless a later spec explicitly delegates that ownership.

#### Inputs / outputs / contracts

- Inputs:
  - runtime objects such as `ExperimentResult`, `ValidationResult`, `WalkForwardResult`, and storage-owned receipts
  - frames and tables produced by canonical runtime modules
  - base output directory and experiment name or workflow label
- Persisted artifact taxonomy:
  - single-run artifacts:
    - `experiment_config.json`
    - `metrics_summary.json`
    - `trade_log.csv`
    - `equity_curve.csv`
    - `report.html` when a single-run report is generated
  - search artifacts:
    - `ranked_results.csv`
    - `runs/run_###/experiment_config.json`
    - `runs/run_###/metrics_summary.json`
    - `runs/run_###/trade_log.csv`
    - `runs/run_###/equity_curve.csv`
    - `best_report.html` when a best-search report is generated
    - `search_report.html` when a search comparison report is generated
  - validation artifacts:
    - `validation_summary.json`
    - `train_ranked_results.csv`
    - `train_best/experiment_config.json`
    - `train_best/metrics_summary.json`
    - `train_best/trade_log.csv`
    - `train_best/equity_curve.csv`
    - `test_selected/experiment_config.json`
    - `test_selected/metrics_summary.json`
    - `test_selected/trade_log.csv`
    - `test_selected/equity_curve.csv`
  - walk-forward artifacts:
    - `walk_forward_summary.json`
    - `fold_results.csv`
    - `folds/fold_###/train_search/ranked_results.csv`
    - `folds/fold_###/train_search/runs/run_###/experiment_config.json`
    - `folds/fold_###/train_search/runs/run_###/metrics_summary.json`
    - `folds/fold_###/train_search/runs/run_###/trade_log.csv`
    - `folds/fold_###/train_search/runs/run_###/equity_curve.csv`
    - `folds/fold_###/test_selected/experiment_config.json`
    - `folds/fold_###/test_selected/metrics_summary.json`
    - `folds/fold_###/test_selected/trade_log.csv`
    - `folds/fold_###/test_selected/equity_curve.csv`
  - diagnostic artifacts:
    - `permutation_test_summary.json`
    - `permutation_scores.csv`
- Canonical output root semantics:
  - `output_dir / experiment_name` is the root for each top-level workflow.
  - nested workflow-specific subdirectories are derived from that root by storage-owned rules.
- Figure placement semantics:
  - no standalone figure/image files are canonical in the current storage contract;
  - figures are embedded in persisted HTML report artifacts unless a later storage spec explicitly adds separate image output.

#### Invariants

- Persisted artifact filenames are stable storage-owned contracts.
- Canonical path derivation happens once in storage-owned code, not separately in runner, CLI, or report code.
- The same workflow mode always writes to the same conceptual directory structure regardless of which caller triggered it.
- Storage outputs may include presentation refs, but those refs do not change the canonical persisted artifact set.

#### Cross-module dependencies

- `experiment_runner.py` requests persistence and consumes returned receipts and derived path references.
- `report.py` and `search_reporting.py` may write HTML report files, but they must do so using storage-owned path conventions.
- `cli.py` may print storage-owned paths, but it must not invent new filename or directory rules.
- `schemas.py` provides runtime objects that storage serializes, but it does not own the persisted schema.
- `README.md`, `PROJECT_BRIEF.md`, and docstrings are derived documentation and must not redefine the layout contract.

#### Failure modes if this boundary is violated

- Search, validation, and walk-forward layouts drift because each workflow reconstructs its own path tree.
- Report links break because presentation modules guess a different root or filename than storage actually wrote.
- CLI payloads advertise artifact paths that do not exist because they were assembled from ad hoc path logic.
- Runtime result objects gain persistence-specific fields that callers then mistake for canonical result truth.
- Backward compatibility becomes impossible to reason about because the storage contract is split across multiple modules.

#### Migration notes from current implementation

- `storage.py` already writes the canonical single-run, search, validation, and walk-forward files, but some path naming is still surfaced or reconstructed elsewhere.
- `storage.py` also owns the canonical permutation/null-comparison summary and score-list artifacts once that diagnostic is enabled.
- The permutation summary now records the block-based null semantics explicitly via `permutation_mode` and `block_size`.
- `experiment_runner.py` currently builds workflow roots such as `search_root`, `validation_root`, and `walk_forward_root`.
- `search_reporting.py` currently knows `best_report.html` and `search_report.html`.
- `cli.py` currently surfaces derived presentation refs like `report_path` and `search_report_path`.
- `schemas.py` currently contains runtime fields that serialize to persistence-facing payloads, which makes the runtime/persistence boundary easy to blur.

#### Open questions / deferred decisions

- Whether standalone figure/image artifacts should ever become canonical persisted outputs is deferred.
  - Recommended default: keep figures inline in HTML reports and add separate image artifacts only through a future storage spec.
- Whether report HTML file placement should be expanded to a richer storage-owned manifest later is deferred.
  - Recommended default: keep the current filenames stable and only add new report artifacts through explicit storage-owned filenames.

#### Scenario: single-run persistence uses one storage-owned layout

- GIVEN a single experiment run is persisted
- WHEN storage writes the canonical files
- THEN the run directory SHALL contain the single-run file set owned by storage
- AND any report HTML SHALL be placed according to the storage-owned report placement rule
- AND no downstream module SHALL need to reconstruct the directory tree to find the artifacts

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
