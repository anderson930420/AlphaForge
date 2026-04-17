# Tasks

## 1. Spec alignment

- [x] 1.1 Add an OpenSpec delta for the MA search-space and candidate-selection contract.
- [x] 1.2 Document the canonical MA search parameters, invalid-combo filtering, ranking semantics, top-N semantics, and search summary/output contract.

## 2. Implementation

- [x] 2.1 Add an explicit MA search-space evaluation contract in `src/alphaforge/search.py`.
- [x] 2.2 Add deterministic ranking and top-N helpers in `src/alphaforge/scoring.py`.
- [x] 2.3 Thread a runner-owned search summary contract through `src/alphaforge/experiment_runner.py` and keep `src/alphaforge/cli.py` presentation-only.
- [x] 2.4 Update serializers/helpers only where needed to surface the stable search summary fields cleanly.

## 3. Verification

- [x] 3.1 Add or update tests covering valid and invalid MA parameter combinations.
- [x] 3.2 Add or update tests covering deterministic ranking and tie-breaking.
- [x] 3.3 Add or update tests covering top-N selection semantics and `best_result` consistency.
- [x] 3.4 Add or update tests covering the stable search summary/output contract and artifact refs.

## 4. Docs and cleanup

- [x] 4.1 Update README only if the user-facing search summary contract changed materially.
- [x] 4.2 Log the implementation and verification steps back to project memory.
