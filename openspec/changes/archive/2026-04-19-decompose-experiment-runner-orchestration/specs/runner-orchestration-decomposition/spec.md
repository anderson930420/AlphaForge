# Delta for Runner Orchestration Decomposition

## ADDED Requirements

### Requirement: `experiment_runner.py` is a public façade and compatibility layer only

`src/alphaforge/experiment_runner.py` SHALL remain the public runner entry point module, but it SHALL delegate workflow implementation to internal orchestration modules and SHALL NOT remain the canonical owner of workflow-specific implementation details.

#### Purpose

- Keep the public runner API stable while reducing the amount of orchestration code concentrated in one module.
- Preserve the frozen runtime contracts while making the runner implementation structure match the orchestration-only boundary already defined by the runtime contract spec.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` is the canonical owner of public runner entry points and compatibility bundles only.
- The public runner-facing compatibility artifacts currently include:
  - `ExperimentExecutionOutput`
  - `SearchExecutionOutput`
- The module is not the canonical owner of internal workflow implementation logic.

#### Allowed responsibilities

- Expose the public runner functions used by CLI and tests.
- Preserve public function signatures and return-shape compatibility.
- Wrap internal workflow outputs into existing public runner bundles when needed for backward compatibility.
- Delegate workflow implementation to `runner_workflows.py`.

#### Explicit non-responsibilities

- `experiment_runner.py` MUST NOT own the single-run, search, validation, or walk-forward implementation logic.
- `experiment_runner.py` MUST NOT own shared split/fold helpers once they are extracted.
- `experiment_runner.py` MUST NOT become the canonical owner of workflow metadata assembly, report/storage wiring, or workflow sequencing internals.
- `experiment_runner.py` MUST NOT reintroduce runtime contract ownership, metric formulas, benchmark formulas, report rendering, or persistence semantics.

#### Inputs / outputs / contracts

- Inputs remain the existing public runner inputs:
  - `DataSpec`
  - `StrategySpec`
  - `BacktestConfig`
  - search, validation, and walk-forward workflow parameters
- Outputs remain the existing public runner outputs and bundles:
  - `ExperimentResult`
  - `ExperimentExecutionOutput`
  - `SearchExecutionOutput`
  - `ValidationResult`
  - `WalkForwardResult`
- The public façade MAY continue to expose the same return types even if the internal workflow implementation changes location.

#### Invariants

- Public runner behavior stays compatible unless a current inconsistency is explicitly documented.
- The public façade does not own execution truth; it only forwards to the workflow owner.
- The façade does not gain new business rules while it is being thinned.

#### Cross-module dependencies

- `cli.py` continues to depend on this public façade.
- `runner_workflows.py` becomes the internal implementation target.
- `runner_protocols.py` supplies shared helper logic for the workflow implementation.

#### Failure modes if this boundary is violated

- The runner remains a hidden god module even after the runtime contract freeze.
- Workflow behavior becomes harder to change because implementation details are still spread across one façade file.
- Any future orchestration refactor must again unwind mixed public and internal responsibilities from the same module.

#### Migration notes from current implementation

- The public functions already exist and must remain callable with the same inputs.
- The current internal orchestration logic should move out of this file rather than being rewritten.
- Existing public output bundles may stay here for compatibility while the workflow implementation moves away.

#### Open questions / deferred decisions

- Whether the public compatibility bundles should later move into a narrower runner-output module is intentionally deferred.
- Whether any private helper dataclasses are needed inside the internal workflow module is intentionally deferred as an implementation detail.

#### Scenario: public runner calls still work after delegation

- GIVEN a caller imports `run_experiment`, `run_search`, `run_validate_search`, or `run_walk_forward_search` from `experiment_runner.py`
- WHEN the caller executes one of those functions
- THEN the public API SHALL still return the same runtime contracts or compatibility bundles as before
- AND the caller SHALL NOT need to know whether the internal implementation lives in a new module

### Requirement: workflow-specific orchestration is owned by `runner_workflows.py`

`src/alphaforge/runner_workflows.py` SHALL own the workflow-specific orchestration logic for single-run, search, validation, and walk-forward execution.

#### Purpose

- Separate the individual workflow paths so each one is easy to inspect without navigating a monolithic runner module.
- Keep workflow sequencing explicit while leaving runtime truth in the frozen canonical modules.

#### Canonical owner

- `src/alphaforge/runner_workflows.py` is the canonical owner of workflow-specific orchestration implementations.
- The owned workflow paths are:
  - single experiment execution
  - grid-search execution
  - validate-search execution
  - walk-forward execution

#### Allowed responsibilities

- Sequence lower-layer calls in the correct workflow order.
- Call `runner_protocols.py` for shared helper logic.
- Call canonical runtime owners such as `backtest.py`, `metrics.py`, `benchmark.py`, `storage.py`, `report.py`, `search_reporting.py`, and `walk_forward_aggregation.py`.
- Assemble workflow outputs using existing runtime and presentation contracts.
- Make the workflow-specific decisions that are purely orchestration choices, such as when to persist outputs or generate reports.

#### Explicit non-responsibilities

- `runner_workflows.py` MUST NOT define execution law, metric formulas, benchmark formulas, or report rendering behavior.
- `runner_workflows.py` MUST NOT define persisted artifact schemas or runtime dataclass schemas.
- `runner_workflows.py` MUST NOT own strategy semantics beyond selecting the appropriate strategy implementation.
- `runner_workflows.py` MUST NOT absorb the specialized owners already established in `search_reporting.py` or `walk_forward_aggregation.py`.

#### Inputs / outputs / contracts

- Inputs:
  - validated market data
  - canonical runtime specs and configs
  - workflow parameters such as split ratios and fold sizes
- Outputs:
  - workflow-level runtime results and/or compatibility bundles
  - optional persistence and report side effects
- Workflow output contracts MUST remain derived from the frozen runtime, presentation, and persistence owners.

#### Invariants

- Each workflow path stays separately named and separately testable.
- Search, validation, and walk-forward logic remain orchestration paths, not schema owners.
- The internal workflow module must not reintroduce code that belongs in `backtest.py`, `metrics.py`, `benchmark.py`, `report.py`, `storage.py`, or `visualization.py`.

#### Cross-module dependencies

- Depends on `runner_protocols.py` for shared workflow helpers.
- Depends on canonical runtime owners for execution, metrics, benchmark summaries, persistence, and report rendering.
- Is invoked by the public façade in `experiment_runner.py`.

#### Failure modes if this boundary is violated

- Workflow-specific logic remains tangled together, which makes later runner decomposition harder than necessary.
- The runner continues to be a hidden central authority even after the runtime boundary freeze.
- Test failures become difficult to localize because multiple workflows still share one implementation body.

#### Migration notes from current implementation

- The current internal functions for single-run, search, validation, and walk-forward orchestration should move here with minimal logic changes.
- Search-report wiring should continue to use the already-separated search reporting module.
- Walk-forward aggregation should continue to use the already-separated aggregation module.

#### Open questions / deferred decisions

- Whether the internal workflow functions should return tuples, private dataclasses, or small internal records is deferred to the implementation step.
- Whether single-run and search workflows should share a private internal execution helper beyond the current public orchestration split is deferred.

#### Scenario: workflow ownership becomes local to the workflow module

- GIVEN the codebase needs to change search or walk-forward sequencing
- WHEN the implementation is updated
- THEN the workflow implementation SHOULD be changed in `runner_workflows.py` rather than in `experiment_runner.py`
- AND the change SHOULD not require editing report, storage, metric, or benchmark owners unless their own contracts change

### Requirement: shared runner helpers are owned by `runner_protocols.py`

`src/alphaforge/runner_protocols.py` SHALL own shared runner-only helper logic that is reused by more than one workflow path and does not belong in the canonical runtime modules.

#### Purpose

- Remove reusable orchestration helpers from the monolithic runner file.
- Keep workflow-specific files focused on workflow sequencing instead of repeated protocol plumbing.

#### Canonical owner

- `src/alphaforge/runner_protocols.py` is the canonical owner of shared runner helper logic.
- The shared helpers include:
  - default `BacktestConfig` assembly from optional input
  - `build_strategy()` dispatch for the current MVP strategy family
  - split-by-ratio helpers for validation
  - train-window validation helpers
  - validation metadata assembly
  - walk-forward fold generation helpers

#### Allowed responsibilities

- Build or coerce runner-local protocol inputs that are reused across multiple workflows.
- Validate orchestration-level preconditions such as split sizes and fold sizes.
- Construct workflow metadata values that describe how a run was segmented.

#### Explicit non-responsibilities

- `runner_protocols.py` MUST NOT own execution semantics, metric formulas, benchmark formulas, report rendering, persistence schemas, or runtime dataclasses.
- `runner_protocols.py` MUST NOT become a general-purpose utility module for unrelated application code.
- `runner_protocols.py` MUST NOT own workflow-specific sequencing decisions.

#### Inputs / outputs / contracts

- Inputs:
  - `BacktestConfig | None`
  - `StrategySpec`
  - market data frames for split/fold helpers
  - workflow sizing parameters
- Outputs:
  - concrete `BacktestConfig`
  - `MovingAverageCrossoverStrategy`
  - train/test splits
  - walk-forward fold indices
  - validation metadata dictionaries
- These helper outputs are orchestration scaffolding only and are not canonical runtime contracts.

#### Invariants

- Shared helpers must remain reusable across at least two workflow paths or they do not belong here.
- Shared helpers must remain free of business logic that belongs in canonical runtime modules.
- Shared helpers must not mutate runtime truth.

#### Cross-module dependencies

- Consumed by `runner_workflows.py`.
- The public façade should not need to know these helper details once the decomposition is complete.

#### Failure modes if this boundary is violated

- Shared orchestration details stay duplicated across workflow functions.
- Runner behavior drifts because each workflow reimplements its own split/fold/default logic.
- Later changes to orchestration protocol require editing too many lines in the public façade.

#### Migration notes from current implementation

- The current helper logic in `experiment_runner.py` for strategy construction, split ratios, window validation, fold generation, and validation metadata should move here.
- Any logic that still exists only to support the current runner monolith should be deleted from `experiment_runner.py` after the move.

#### Open questions / deferred decisions

- Whether any additional runner helper beyond the listed ones should be migrated is intentionally deferred until the first extraction pass is complete.

#### Scenario: shared helper contracts are reused by multiple workflows

- GIVEN validation and walk-forward workflows both need split or fold protocol logic
- WHEN the runner implementation needs those helpers
- THEN it SHOULD call the shared helper in `runner_protocols.py`
- AND it SHOULD not duplicate the same split or fold policy inside each workflow body

