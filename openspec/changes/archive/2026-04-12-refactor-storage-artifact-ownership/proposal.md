# Proposal: refactor-storage-artifact-ownership

## Boundary problem

- `src/alphaforge/schemas.py` currently defines runtime result models and also includes persistence-facing path fields plus `to_dict()` behavior that serializes those runtime models.
- `src/alphaforge/storage.py` currently owns persisted artifact materialization, artifact path creation, JSON/CSV output writing, and partial persisted-result reconstruction by returning mutated result objects with write-time paths attached.
- Artifact schema knowledge is therefore split across runtime dataclasses and persistence functions.
- This split makes it unclear whether a field such as `equity_curve_path`, `validation_summary_path`, or `fold_results_path` is:
  - part of domain/runtime truth,
  - part of persistence output shape,
  - or a write-time side effect.

## Why

- Storage ownership is the paired boundary for the already-accepted experiment-runner orchestration change.
- If runtime contracts continue to carry persistence-only fields by default, later refactors cannot cleanly separate orchestration, serialization, and domain modeling.
- If save/write functions continue to mutate or reconstruct runtime result truth, persisted artifact evolution will silently redefine domain contracts.

## Canonical ownership decision

- `src/alphaforge/schemas.py` remains the single canonical owner of in-memory runtime contracts only.
- `src/alphaforge/storage.py`, or serialization helpers adjacent to storage and owned by storage, becomes the single canonical owner of persisted artifact schemas.
- `storage.py` becomes the authoritative owner of:
  - JSON persistence shapes,
  - CSV persistence shapes,
  - path materialization,
  - output layout,
  - artifact naming,
  - persistence-boundary versioning policy.
- Runtime result objects must lose implicit ownership over persistence-only fields unless a future spec explicitly justifies them as runtime-visible contracts.

## Scope

- Primary modules:
  - `src/alphaforge/schemas.py`
  - `src/alphaforge/storage.py`
- Directly affected callers and consumers:
  - `src/alphaforge/experiment_runner.py`
  - `src/alphaforge/cli.py`
  - `src/alphaforge/report.py`
- Affected artifact families:
  - single experiment JSON/CSV outputs
  - ranked search CSV outputs
  - validation JSON/CSV outputs
  - walk-forward JSON/CSV outputs

## Migration risk

- Existing callers may rely on path fields being present directly on runtime result objects after save functions run.
- Existing tests may implicitly treat `to_dict()` output as both runtime schema and persistence schema.
- Validation and walk-forward summary JSON shape can drift if runtime result models and persisted summary contracts are separated incompletely.
- Backward compatibility expectations for previously written files can be broken if artifact schema changes are not versioned or explicitly assessed.

## Acceptance conditions

- Runtime dataclasses in `schemas.py` represent in-memory runtime truth only.
- Persisted JSON/CSV layout is defined only by storage-owned serializers or storage-owned artifact schema helpers.
- Save/write functions materialize artifact files and paths without redefining domain/runtime truth.
- Path creation, output layout, and artifact naming can be traced to one storage-owned boundary.
- Any evolution of persisted artifact shape is evaluated as a persistence-contract change, not silently absorbed into runtime models.

## Migration note

- `ExperimentResult` no longer carries persisted artifact paths.
- Persisted artifact references now live in storage-owned `ArtifactReceipt`.
- New callers must be receipt-first and must not use runtime result objects as artifact locators.
