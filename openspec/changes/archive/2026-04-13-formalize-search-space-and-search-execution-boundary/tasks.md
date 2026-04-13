# Tasks

## 1. Define the search-space contract in `src/alphaforge/search.py`

- Clarify that the canonical search output is an ordered `list[StrategySpec]`.
- Keep grid expansion and candidate construction in the search owner.

## 2. Freeze ranking ownership in `src/alphaforge/scoring.py`

- Ensure ranking and best-candidate selection remain one canonical contract.
- Keep threshold filtering and descending score order explicit.

## 3. Preserve runner-only orchestration in `src/alphaforge/experiment_runner.py`

- Keep candidate execution, validation reuse, and walk-forward reuse in the runner.
- Avoid adding search-space or ranking logic there.

## 4. Sync search-facing downstream consumers if needed

- Update any docs, tests, or comments that still imply runner or presentation layers own search truth.

## 5. Validate the boundary

- Add or update focused tests if necessary to prove candidate generation, ranking, and runner orchestration remain separated.

