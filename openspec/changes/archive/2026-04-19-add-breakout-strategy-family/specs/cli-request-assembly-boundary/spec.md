# Delta for CLI Request Assembly Boundary

## ADDED Requirements

### Requirement: CLI request assembly supports explicit strategy-family selection for run, search, validate-search, and walk-forward workflows

`src/alphaforge/cli.py` SHALL keep CLI request assembly orchestration-only while allowing a caller to select the strategy family for the core research workflows.

#### Purpose

- Keep the CLI as the request-assembly boundary instead of a second owner of strategy semantics.
- Allow one CLI surface to assemble MA crossover requests or breakout requests without introducing a registry or separate command tree.

#### Canonical owner

- `src/alphaforge/cli.py` remains the canonical owner of command parsing and request DTO assembly.
- `src/alphaforge/experiment_runner.py` remains the canonical owner of workflow orchestration.
- `src/alphaforge/search.py` remains the canonical owner of family-specific candidate construction.

#### Allowed responsibilities

- `cli.py` MAY expose a `--strategy` selector for `run`, `search`, `validate-search`, and `walk-forward`.
- `cli.py` MAY assemble MA crossover request DTOs when the selected family is MA crossover.
- `cli.py` MAY assemble breakout request DTOs when the selected family is breakout.
- `cli.py` MAY keep permutation diagnostics on the current MA-only path if that diagnostic remains family-specific.

#### Explicit non-responsibilities

- `cli.py` MUST NOT infer strategy family from parameter names alone.
- `cli.py` MUST NOT own parameter validity for MA crossover or breakout.
- `cli.py` MUST NOT become a strategy registry framework.
- `cli.py` MUST NOT redefine family-specific search-space semantics or execution semantics.

#### Inputs / outputs / contracts

- Search-like workflow inputs parsed by CLI:
  - strategy family name
  - family-specific parameter values or grids
  - validation split or walk-forward sizing settings
- Family-specific parameter assembly:
  - MA crossover uses `short_window` / `long_window` or `short_windows` / `long_windows`
  - breakout uses `lookback_window` or `lookback_windows`
- CLI output remains derived from authoritative runtime, storage, and report owners.

#### Invariants

- MA crossover remains the default family when the caller does not select another family.
- CLI parsing remains syntactic only; semantic validity is enforced upstream.

#### Scenario: CLI assembles a breakout run request

- GIVEN a user invokes the run command with `--strategy breakout`
- WHEN `cli.py` parses the command
- THEN it SHALL assemble a breakout `StrategySpec`
- AND it SHALL delegate execution to the runner without owning breakout signal semantics

#### Scenario: CLI assembles a breakout search request

- GIVEN a user invokes search-like commands with `--strategy breakout`
- WHEN `cli.py` parses the command
- THEN it SHALL assemble the breakout parameter grid
- AND it SHALL NOT require MA-only parameter names to be present
