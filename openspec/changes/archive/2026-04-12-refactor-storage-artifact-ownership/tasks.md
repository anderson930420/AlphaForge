# Tasks

## 1. Spec and ownership alignment

- [ ] 1.1 Identify every field in `schemas.py` that exists only because storage writes files or materializes paths.
- [ ] 1.2 Identify every persisted JSON/CSV schema currently derived implicitly from runtime dataclasses or `to_dict()` methods.
- [ ] 1.3 Classify every persistence-facing field as `domain result`, `persisted artifact reference`, or `storage residue` before removing or relocating it.

## 2. Serialization boundary refactor

- [ ] 2.1 Move persisted artifact serialization logic under storage-owned helpers or storage-adjacent serializers.
- [ ] 2.2 Ensure JSON and CSV write shapes are defined by storage-owned contracts, not by direct dataclass dumping.
- [ ] 2.3 Ensure save/write functions materialize paths and artifacts without redefining runtime/domain truth.

## 3. Runtime contract cleanup

- [x] 3.1 Remove storage residue fields from runtime result dataclasses once direct callers no longer require them.
- [x] 3.2 Decide field-by-field whether each persisted artifact reference remains temporarily on runtime results or moves into a separate persistence receipt boundary.
- [x] 3.2.a Introduce a storage-owned `ArtifactReceipt` for new callers and migrate runner/report/CLI integrations to receipt-first consumption.
- [x] 3.2.b Mark `ExperimentResult.equity_curve_path` and `trade_log_path` as deprecated during the migration window and direct new callers to `ArtifactReceipt`.
- [x] 3.3 Remove or narrow any remaining runtime serialization behavior that mixes runtime contract export with persistence schema export.
- [x] 3.4 Update orchestration and CLI callers to consume storage-owned persisted artifact outputs explicitly.

## 4. Backward compatibility and verification

- [x] 4.1 Add tests that prove runtime contracts and persisted artifact schemas can evolve independently.
- [x] 4.2 Add tests for artifact naming, output layout, and storage-owned schema version markers or compatibility checks where needed.
- [x] 4.3 Verify that report ownership and orchestration ownership remain unchanged while storage ownership is clarified.
- [x] 4.4 Evaluate whether removing any persisted artifact reference field changes the public runtime API, and document the compatibility decision explicitly.
- [x] 4.5 Add regression tests proving that `ExperimentResult` remains valid runtime/domain truth without artifact paths and that `ArtifactReceipt` alone is sufficient for report/comparison artifact linking.

## 5. Cleanup

- [x] 5.1 Delete stale serialization assumptions from `schemas.py`, `experiment_runner.py`, and callers after migration.
- [x] 5.2 Update documentation only after storage-owned persistence contracts are the single source of truth.
