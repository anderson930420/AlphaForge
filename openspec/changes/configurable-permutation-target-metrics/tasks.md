# Tasks

## 1. Spec and contract alignment

- [x] 1.1 Update the permutation diagnostic spec to make target-metric selection explicit and to require integer-safe count serialization.
- [x] 1.2 Update the artifact-layout and CLI boundary specs so the new `--target-metric` request shape and generic metric-value fields are canonical.

## 2. Code migration

- [x] 2.1 Add supported target-metric selection to `src/alphaforge/permutation.py` and thread the selected metric through real and permuted evaluations.
- [x] 2.2 Update `src/alphaforge/schemas.py` and `src/alphaforge/storage.py` so the permutation summary uses metric-value naming and normalizes integer fields before writing JSON.
- [x] 2.3 Add the `--target-metric` CLI option and pass it through to the diagnostic runner without introducing new business logic in `cli.py`.

## 3. Verification

- [x] 3.1 Add tests for deterministic permutation behavior with `score` and `sharpe_ratio`.
- [x] 3.2 Add tests for invalid target-metric rejection and for integer typing in persisted summary JSON.
- [x] 3.3 Add CLI/storage consistency tests for the updated permutation summary payload.

## 4. Cleanup

- [x] 4.1 Update the README only if the new permutation option changes the documented user-facing command surface.
- [x] 4.2 Update the local worklog after implementation and before archive.
