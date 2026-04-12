# storage-artifact-ownership Specification

## Purpose
TBD - created by archiving change refactor-storage-artifact-ownership. Update Purpose after archive.
## Requirements
### Requirement: Runtime contracts and persisted artifact schemas are separate contracts

Persisted artifact schemas SHALL be owned by `src/alphaforge/storage.py` or storage-owned serializers adjacent to it, and in-memory runtime contracts SHALL be owned by `src/alphaforge/schemas.py`; overlapping fields do not make the two contracts identical.

#### Purpose

- Define a clean boundary between runtime result contracts and persisted artifact contracts.
- Prevent storage-layer concerns from leaking backward into domain/runtime truth.
- Make later persistence refactors possible without changing runtime dataclass meaning by accident.

#### Canonical owner

- `src/alphaforge/schemas.py` is the single authoritative owner of in-memory runtime result contracts.
- `src/alphaforge/storage.py` is the single authoritative owner of persisted artifact schemas.
- If serialization helpers are introduced next to storage, they remain storage-owned and do not become a second contract owner.

#### Allowed responsibilities

- `schemas.py` may define runtime dataclasses and shared typed structures used in memory during execution.
- `storage.py` may define JSON payload shapes, CSV column layouts, output directory trees, artifact filenames, and write-time metadata included in persisted artifacts.
- `storage.py` may define explicit conversion from runtime objects to persisted artifact payloads.
- `storage.py` may define schema version markers or compatibility metadata for persisted artifacts.

#### Explicit non-responsibilities

- `schemas.py` MUST NOT own JSON persistence shape, CSV column order, output file naming, output directory layout, or write-time file path materialization.
- `storage.py` MUST NOT redefine runtime/domain truth such as metric formulas, benchmark formulas, strategy semantics, or workflow protocol semantics.
- Save/write functions MUST NOT mutate runtime truth in order to make persisted files easier to write.
- `storage.py` MUST NOT absorb experiment orchestration ownership, report content ownership, or visualization semantics.

#### Inputs / outputs / contracts

- Runtime contract scope:
  - in-memory `ExperimentResult`, `ValidationResult`, `WalkForwardResult`, and related nested dataclasses
  - runtime-only metadata that is meaningful before persistence occurs
- Persistence contract scope:
  - `experiment_config.json`
  - `metrics_summary.json`
  - `ranked_results.csv`
  - `validation_summary.json`
  - `walk_forward_summary.json`
  - `fold_results.csv`
  - any storage-owned path manifest or schema-version marker introduced later
- Conversion boundary:
  - runtime object in
  - storage-owned serializer converts runtime fields into persisted JSON/CSV payloads
  - storage-owned path materializer determines where files are written
  - persisted artifact paths may be returned as persistence outputs, but they are not automatically domain truth
- Field classification rules:
  - domain result fields:
    - fields whose meaning exists even when no artifact has been written
    - examples in the current repository: `data_spec`, `strategy_spec`, `backtest_config`, `metrics`, `score`, `split_config`, `selected_strategy_spec`, `test_benchmark_summary`, `walk_forward_config`, `aggregate_test_metrics`, `aggregate_benchmark_metrics`, fold date bounds
  - persisted artifact reference fields:
    - fields whose only meaning is to identify a persisted artifact already materialized by storage
    - current examples: `equity_curve_path`, `trade_log_path`, `metrics_path`, `validation_summary_path`, `train_ranked_results_path`, `walk_forward_summary_path`, `fold_results_path`
  - storage residue fields:
    - fields whose only purpose is to support storage bookkeeping, directory traversal, or file-layout convenience rather than domain/runtime semantics
    - current example: `fold_path`
  - storage residue fields MUST NOT remain in runtime result contracts once callers can obtain the same information from storage-owned outputs
- persisted artifact reference fields MAY remain temporarily in runtime result contracts during migration, but they MUST be treated as persistence-boundary outputs rather than domain truth
 - when a storage-owned receipt exists for the same artifact references, new callers MUST consume the receipt instead of reading deprecated runtime path fields

#### Invariants

- Runtime dataclass structure and persisted artifact schema are separate contracts even when they share field names.
- Persistence-specific fields such as file paths, output locations, and write-only metadata MUST NOT leak backward into runtime result objects unless a later spec explicitly justifies them as runtime-visible truth.
- Storage-owned serializers MUST derive persisted payloads from runtime objects without redefining the meaning of runtime fields.
- Artifact naming and directory layout MUST have one authoritative owner in storage.
- Persisted artifact evolution MUST be evaluated as a persistence-boundary compatibility change, not as an implicit runtime-contract change.
- If a field is classified as storage residue, it MUST NOT be treated as part of domain result truth, CLI contract truth, or report contract truth.
- If a field is classified as persisted artifact reference, any caller that consumes it MUST treat it as an optional artifact locator, not as the authoritative source of the underlying domain value.

#### Cross-module dependencies

- `storage.py` depends on runtime contracts from `schemas.py` as input material only.
- `experiment_runner.py` depends on storage-owned persistence outputs but does not own their schema.
- `cli.py` may display persisted artifact paths but does not own their naming or layout.
- `report.py` may save report files, but report content remains report-owned while file-level artifact layout rules remain storage-owned only if storage is explicitly chosen as the path owner for report outputs.

#### Failure modes if this boundary is violated

- Runtime dataclasses gain persistence-only fields and stop representing purely in-memory execution state.
- Save functions redefine domain truth by reconstructing result objects with write-time paths that callers then mistake for authoritative runtime fields.
- JSON and CSV shapes drift when `to_dict()` methods and storage writers evolve independently.
- Backward compatibility breaks silently because artifact schema changes are treated as harmless runtime refactors instead of persistence-contract changes.
- Orchestration and CLI start depending on incidental dataclass serialization rather than explicit storage contracts.

#### Migration notes from current implementation

- `ExperimentResult`, `ValidationResult`, `WalkForwardFoldResult`, and `WalkForwardResult` currently contain persistence-facing path fields.
- `to_dict()` methods in `schemas.py` currently serialize runtime objects into persistence-friendly dictionaries.
- `save_single_experiment()`, `save_validation_result()`, and `save_walk_forward_result()` currently return reconstructed runtime objects whose fields incorporate write-time paths.
- `storage.py` currently owns artifact writing, but some artifact shape knowledge still lives in `schemas.py`.
- Current field classification audit:
  - `ExperimentResult.equity_curve_path`, `trade_log_path`, `metrics_path`: persisted artifact references
  - `ValidationResult.validation_summary_path`, `train_ranked_results_path`: persisted artifact references
  - `WalkForwardResult.walk_forward_summary_path`, `fold_results_path`: persisted artifact references
  - `WalkForwardFoldResult.fold_path`: storage residue
- Migration rule:
  - persisted artifact reference fields may remain temporarily during caller migration
  - storage residue fields should be removed first unless a caller can justify them as explicit artifact-reference contract

#### Open questions / deferred decisions

- Whether persistence outputs should be represented by separate storage-owned dataclasses, plain dictionaries, or serializer functions only.
- Whether report file paths should stay report-owned or be formalized as storage-owned artifact layout once report persistence is revisited.
- Whether schema version markers should be stored inside every JSON artifact, only summary artifacts, or a storage-owned manifest.
- Whether persisted artifact references should remain attached to runtime results after save operations, or whether save operations should instead return separate persistence receipts.
- During the transition where both exist, runtime path fields MUST be documented as deprecated and new caller integrations MUST target the storage-owned receipt first.

#### Scenario: Runtime results exist before any artifact is written

- GIVEN a workflow completes execution in memory without writing outputs
- WHEN runtime result objects are inspected
- THEN those objects SHALL be valid runtime contracts without requiring persisted file paths to exist
- AND the meaning of those objects SHALL NOT depend on storage side effects

#### Scenario: Persisted artifact schema is storage-owned even when fields overlap runtime models

- GIVEN a runtime result shares field names with a JSON or CSV artifact
- WHEN storage writes the artifact
- THEN storage-owned serializers SHALL define the persisted field set, layout, and naming
- AND the persisted artifact SHALL be treated as a separate contract from the runtime dataclass structure

#### Scenario: Save functions do not redefine domain truth

- GIVEN a save function writes files for an experiment or validation workflow
- WHEN the write completes
- THEN the save function SHALL materialize persisted artifacts and paths without changing the canonical meaning of runtime result fields
- AND any persistence-specific outputs SHALL be clearly treated as persistence-boundary outputs rather than silently injected domain truth

#### Scenario: Storage residue does not survive as runtime truth

- GIVEN a field exists only to support storage directory traversal or layout bookkeeping
- WHEN the field is audited against runtime usage
- THEN that field SHALL be classified as storage residue
- AND storage residue SHALL NOT remain in runtime contracts unless a later spec upgrades it into an explicit persisted artifact reference contract

#### Scenario: Persisted artifact evolution is evaluated for backward compatibility

- GIVEN a persisted JSON or CSV artifact shape changes
- WHEN that change is proposed
- THEN the change SHALL be evaluated as a persistence-contract compatibility change
- AND the proposal SHALL state whether older artifacts remain readable, require migration, or are intentionally unsupported

