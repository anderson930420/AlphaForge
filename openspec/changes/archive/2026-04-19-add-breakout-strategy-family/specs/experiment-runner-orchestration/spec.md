# Delta for Experiment Runner Orchestration

## ADDED Requirements

### Requirement: search-like runner workflows accept an explicit strategy family and delegate family-specific candidate construction upstream

`src/alphaforge/experiment_runner.py` SHALL keep runner orchestration-only behavior while allowing search, validate-search, and walk-forward workflows to operate on a named strategy family instead of assuming MA crossover.

#### Purpose

- Keep the public runner façade stable while allowing a second supported family to use the same workflow orchestration paths.
- Prevent search-like workflows from inferring strategy family from parameter names alone.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` remains the public runner façade and compatibility bundle owner.
- `src/alphaforge/runner_workflows.py` remains the workflow sequencing owner.
- `src/alphaforge/search.py` remains the canonical owner of family-specific candidate construction.

#### Allowed responsibilities

- `experiment_runner.py` MAY expose an explicit strategy-family selector for search-like workflows.
- `runner_workflows.py` MAY pass that strategy-family selector into `search.py` and into runner-local validation helpers.

#### Explicit non-responsibilities

- `experiment_runner.py` MUST NOT infer breakout support from parameter names or from MA-specific defaults.
- `experiment_runner.py` MUST NOT become a hidden strategy registry.
- `experiment_runner.py` MUST NOT own family-specific parameter validity.

#### Inputs / outputs / contracts

- Search-like workflow inputs now include:
  - strategy family name
  - family-specific parameter grid
  - split or walk-forward protocol settings
- Outputs remain the same public runner bundles and runtime results.

#### Invariants

- MA crossover remains the default supported family unless the caller explicitly selects breakout.
- The public runner API stays orchestration-only; the chosen family only affects candidate construction, strategy dispatch, and family-specific search validation.

#### Scenario: breakout search uses the same runner workflow path with a different family selector

- GIVEN a caller selects the breakout family for search-like execution
- WHEN the runner executes search, validate-search, or walk-forward
- THEN it SHALL delegate candidate construction to the family-aware search owner
- AND it SHALL preserve the same runtime, evidence, policy, storage, and report owners
