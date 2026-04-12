# Tasks

## 1. Spec and contract alignment

- [ ] 1.1 Add the runner decomposition specification naming `experiment_runner.py` as a public façade, `runner_workflows.py` as the workflow owner, and `runner_protocols.py` as the shared helper owner.
- [ ] 1.2 Identify the exact helper functions and workflow bodies that must move out of `experiment_runner.py`.

## 2. Code migration

- [ ] 2.1 Introduce `src/alphaforge/runner_workflows.py` and move the single-run, search, validate-search, and walk-forward orchestration bodies into it.
- [ ] 2.2 Introduce `src/alphaforge/runner_protocols.py` and move shared orchestration helpers into it.
- [ ] 2.3 Reduce `src/alphaforge/experiment_runner.py` to a thin compatibility façade that delegates to the new internal modules and preserves the public output bundles.
- [ ] 2.4 Remove duplicate helper bodies and repeated backtest-config assembly from the public façade once the new modules are wired in.

## 3. Verification

- [ ] 3.1 Add or update focused tests that prove the public runner entry points still produce the same behavior after delegation.
- [ ] 3.2 Add focused tests for runner helper behavior that now lives in `runner_protocols.py`.
- [ ] 3.3 Verify single-run, search, validate-search, and walk-forward workflows still pass their existing behavior-preserving tests.

## 4. Cleanup

- [ ] 4.1 Delete stale compatibility helpers from `experiment_runner.py` after the new workflow modules are active.
- [ ] 4.2 Update the local worklog and Obsidian notes with the runner decomposition milestone.

