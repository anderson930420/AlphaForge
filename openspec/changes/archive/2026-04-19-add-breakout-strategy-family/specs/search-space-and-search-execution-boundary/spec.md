# Delta for Search Space and Search Execution Boundary

## ADDED Requirements

### Requirement: `search.py` is the canonical owner of named strategy-family search-space construction

`src/alphaforge/search.py` SHALL be the single authoritative owner of search-space generation and candidate construction for the supported strategy families.

#### Supported strategy families

- `ma_crossover`
- `breakout`

#### Canonical parameter contracts

- MA crossover family:
  - `short_window`
  - `long_window`
  - both parameters MUST be positive integers
  - `short_window` MUST be smaller than `long_window`
- Breakout family:
  - `lookback_window`
  - `lookback_window` MUST be a positive integer

#### Coarse-search semantics

- family-local search SHALL be a deterministic Cartesian expansion over the provided parameter lists
- parameter enumeration order MUST follow the parameter-grid key order
- candidate value order for each parameter MUST follow the input list order
- each candidate SHALL bind one explicit strategy family name to one parameter combination
- invalid combinations MUST be filtered explicitly before candidate execution
- invalid filtering MUST be deterministic for the same input grid and family name

#### Invalid-combo handling contract

- invalid combinations SHALL be excluded from the returned candidate list
- invalid combinations MUST NOT be silently repaired or mutated into valid combinations
- if every attempted combination is invalid, the search-space owner SHALL raise a clear error instead of returning an empty valid-candidate set
- search-space evaluation output SHOULD expose attempted, valid, and invalid counts so downstream workflows can report the filtering result without re-deriving it

#### Scenario: MA and breakout candidate grids become ordered StrategySpec candidates

- GIVEN a parameter grid for the MA crossover family or the breakout family
- WHEN the search-space owner evaluates that grid
- THEN it SHALL produce an ordered `list[StrategySpec]`
- AND each candidate SHALL carry the selected family name in `StrategySpec.name`

### Requirement: strategy modules own family-specific semantic validity; search owns enumeration only

`src/alphaforge/strategy/*` SHALL own strategy-specific semantic validity, while `src/alphaforge/search.py` SHALL own enumeration and candidate construction only.

#### Purpose

- Prevent a strategy implementation and the search owner from both acting as final validators for the same parameter rule.
- Keep semantic validity where the strategy implementation can enforce it at construction or signal-generation time.

#### Canonical owner

- `src/alphaforge/strategy/base.py` remains the owner of the strategy interface contract.
- `src/alphaforge/strategy/ma_crossover.py` remains the owner of MA crossover parameter validity and MA-specific strategy semantics.
- `src/alphaforge/strategy/breakout.py` becomes the owner of breakout parameter validity and breakout-specific strategy semantics.
- `src/alphaforge/search.py` remains the owner of candidate enumeration and search-family-local pruning.

#### Allowed responsibilities

- Strategy modules MAY:
  - reject semantically invalid `StrategySpec` values for their own family,
  - enforce construction-time invariants such as positive lookback lengths or ordering constraints,
  - define candidate semantics that are unique to that strategy family.
- `search.py` MAY:
  - prefilter combinations that are impossible to instantiate for the target family,
  - use family-local pruning as a search optimization,
  - keep the candidate list deterministic and reusable.

#### Explicit non-responsibilities

- Strategy modules MUST NOT own generic Cartesian enumeration rules.
- `search.py` MUST NOT become the final semantic validator for strategy families.
- `search.py` MUST NOT encode execution, metric, or benchmark semantics under the guise of candidate validity.
- `search.py` MUST NOT invent hidden strategy-specific policy beyond the search-family constraints it explicitly owns.

#### Inputs / outputs / contracts

- Strategy-specific validity inputs:
  - `StrategySpec`
  - strategy-family parameters
  - strategy constructor or family-level invariants
- Search-space inputs:
  - strategy family name
  - parameter grid
- Contract rule:
  - search-space generation may avoid impossible candidates, but the strategy implementation remains the source of truth for whether a candidate is semantically valid for that strategy family

#### Invariants

- Candidate construction and semantic validity are related but not identical.
- Search-space pruning does not replace strategy validation.
- A candidate that survives search-space generation must still be accepted or rejected by the strategy owner according to its own rules.

#### Scenario: breakout validity remains breakout-owned

- GIVEN a candidate `StrategySpec` reaches the breakout strategy implementation
- WHEN the strategy is constructed
- THEN the breakout implementation SHALL enforce its own parameter invariants
- AND search-space generation SHALL NOT be treated as the final validator
