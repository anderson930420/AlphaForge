# Proposal: decompose-experiment-runner-orchestration

## Boundary problem

- `src/alphaforge/experiment_runner.py` still centralizes single-run, search, validation, and walk-forward orchestration in one module even though the core runtime contracts are already frozen.
- The module also owns shared runner helpers such as strategy construction, train/test splitting, train-window validation, fold generation, and workflow metadata assembly.
- That concentration makes the orchestration layer harder to reason about than the already-frozen architecture requires, because one file still contains multiple workflow seams that could be separated without changing runtime truth.

## Canonical ownership decision

- `src/alphaforge/experiment_runner.py` becomes the public compatibility façade for runner entry points and runner-local output bundles only.
- `src/alphaforge/runner_workflows.py` becomes the canonical owner of workflow-specific orchestration implementations for single-run, search, validation, and walk-forward execution.
- `src/alphaforge/runner_protocols.py` becomes the canonical owner of shared runner-only helpers such as strategy construction, split/fold generation, train-window validation, and workflow metadata assembly.
- `src/alphaforge/search_reporting.py` and `src/alphaforge/walk_forward_aggregation.py` remain specialized helper owners and must not be reabsorbed into the runner.

## Scope

- Affected public runner entry points:
  - `run_experiment`
  - `run_experiment_with_artifacts`
  - `run_search`
  - `run_search_with_details`
  - `run_validate_search`
  - `run_walk_forward_search`
- Affected runner-local helper responsibilities:
  - strategy construction
  - default backtest config assembly
  - market-data split helpers
  - train-window validation
  - validation metadata assembly
  - walk-forward fold generation
- Affected tests:
  - single-run workflow tests
  - search workflow tests
  - validate-search workflow tests
  - walk-forward workflow tests

## Migration risk

- Public API behavior must remain compatible, including result ordering, saved artifact paths, and workflow outputs.
- If the runner is split too aggressively, the codebase can end up with tiny modules that are harder to navigate than the current monolith.
- If shared helpers are moved without a clear boundary, validation and walk-forward workflows can end up with duplicated protocol logic.
- If the public façade stops being stable, CLI behavior and tests that import runner entry points will drift even though the frozen runtime contracts should stay unchanged.

## Acceptance conditions

- `experiment_runner.py` is materially thinner and no longer contains the internal workflow implementations.
- Workflow-specific orchestration paths are separated into clearer internal units.
- Shared runner helpers no longer sit unnecessarily inside one monolithic runner module.
- No core runtime contracts, metric formulas, benchmark formulas, report rendering behavior, or persistence contracts change.
- Existing workflow tests still pass, and any new tests remain behavior-preserving and contract-oriented.

## Follow-up changes

- `normalize-persistence-artifact-contracts`

