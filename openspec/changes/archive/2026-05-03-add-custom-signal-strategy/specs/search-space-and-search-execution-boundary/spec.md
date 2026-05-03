# search-space-and-search-execution-boundary Specification

## Purpose

Define the canonical named strategy-family search-space contract, including parameter enumeration, invalid-combination filtering, ranking handoff, and stable search-summary semantics.

## MODIFIED Requirements

### Requirement: `search.py` is the canonical owner of search-space generation and candidate construction

`src/alphaforge/search.py` SHALL be the single authoritative owner of AlphaForge search-space generation and candidate construction semantics for the supported strategy families.

#### Scenario: parameter grids become ordered StrategySpec candidates

- GIVEN a parameter grid for the MA crossover search family
- WHEN `search.py` expands the grid
- THEN it SHALL produce an ordered `list[StrategySpec]`
- AND that list SHALL be the canonical search-space contract consumed by the runner

#### Scenario: search-space generation does not execute strategies

- GIVEN a candidate `StrategySpec` list has been generated
- WHEN the search workflow continues
- THEN `search.py` SHALL NOT run backtests or compute scores
- AND execution SHALL be delegated to the orchestration owner

## ADDED Requirements

### Requirement: validation-only custom-signal workflows are not search-space families

`src/alphaforge/search.py` SHALL reject `custom_signal` as a search-space family and SHALL NOT enumerate it as a grid-search candidate family.

#### Scenario: custom_signal is routed to research validation, not search

- GIVEN a caller asks `search.py` to build candidates for `custom_signal`
- WHEN search-space generation runs
- THEN AlphaForge SHALL raise a clear error
- AND the error SHALL indicate that `custom_signal` is validation-only rather than search-capable
- AND search-space generation SHALL NOT attempt to infer parameter-grid semantics for `signal.csv`
