# Design: decompose-experiment-runner-orchestration

## Canonical ownership mapping

- `src/alphaforge/experiment_runner.py`
  - keep public entry points and compatibility bundles
  - remove internal workflow implementation bodies
- `src/alphaforge/runner_workflows.py`
  - own the concrete orchestration for single-run, search, validation, and walk-forward paths
- `src/alphaforge/runner_protocols.py`
  - own shared orchestration helpers reused across workflow paths

## Contract migration plan

- Keep the public runner API unchanged so CLI and tests do not need to learn a new external contract.
- Move the current private workflow implementations out of `experiment_runner.py` into `runner_workflows.py`.
- Move shared protocol helpers out of `experiment_runner.py` into `runner_protocols.py`.
- Keep `ExperimentExecutionOutput` and `SearchExecutionOutput` available from the public façade to preserve caller compatibility while the internal structure changes.
- Preserve the already-frozen runtime, presentation, and persistence contracts by treating the new modules as orchestration-only consumers.

## Duplicate logic removal plan

- Remove repeated default `BacktestConfig` construction from the public façade by introducing a shared helper in `runner_protocols.py`.
- Remove `build_strategy()` from the public façade if it remains runner-scoped shared orchestration logic.
- Remove `_split_market_data_by_ratio()`, `_validate_train_windows()`, `_build_validation_metadata()`, and `_generate_walk_forward_folds()` from the public façade after moving them to the protocol module.
- Remove workflow bodies from the public façade after the internal workflow module is in place.
- Keep `search_reporting.py` and `walk_forward_aggregation.py` where they are; do not move those responsibilities back into the runner.

## Verification plan

- Add tests that public runner entry points still return the same public outputs and still persist the same artifacts.
- Add tests that patch `runner_workflows.py` from `experiment_runner.py` to prove the façade delegates rather than inlines the workflow logic.
- Add tests for `runner_protocols.py` helpers where the helper contract is easiest to observe:
  - split ratio validation
  - walk-forward fold generation
  - validation metadata assembly
- Keep the focused single-run, search, validate-search, and walk-forward tests behavior-preserving so they continue to describe public behavior rather than internals.

## Temporary migration states

- During the move, `experiment_runner.py` may temporarily contain thin wrapper functions that forward to `runner_workflows.py` while still exporting the compatibility bundles.
- Any temporary duplication of helper logic between the façade and protocol module must be removed as soon as the workflow tests pass and the public output remains stable.
- No runtime contract duplication is expected; if a runtime contract starts to drift during the migration, the move must pause and the contract must be rechecked against `define-core-runtime-contracts`.

