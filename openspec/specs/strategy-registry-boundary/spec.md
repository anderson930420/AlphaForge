# strategy-registry-boundary Specification

## Purpose
TBD - created by archiving change formalize-strategy-registry-boundary. Update Purpose after archive.
## Requirements
### Requirement: Strategy registry owns supported family metadata

`src/alphaforge/strategy_registry.py` SHALL be the canonical owner of supported strategy-family metadata.

#### Scenario: supported families are registry-owned

- GIVEN AlphaForge exposes supported strategy families
- WHEN search, runner, protocol, permutation, or CLI code needs the supported family set
- THEN that code SHALL derive the family names from the strategy registry
- AND it SHALL NOT maintain an independent supported-family source of truth
- AND the current supported family set SHALL remain exactly `ma_crossover` and `breakout`

#### Scenario: unsupported strategy names fail clearly

- GIVEN a caller asks for a strategy family that is not registered
- WHEN the registry lookup or registry-backed construction runs
- THEN AlphaForge SHALL raise a clear error
- AND the error SHALL include the unsupported strategy name
- AND the error SHALL include the supported strategy-family names

### Requirement: Strategy registry owns construction dispatch

The strategy registry SHALL own construction from `StrategySpec` to the shared `Strategy` interface for registered families.

#### Scenario: runner construction uses registry dispatch

- GIVEN a `StrategySpec` for `ma_crossover` or `breakout`
- WHEN runner, protocol, or permutation code needs a concrete strategy instance
- THEN it SHALL call registry-backed construction
- AND it SHALL NOT define separate `if` / `elif` construction dispatch for those families

#### Scenario: concrete strategy modules retain semantic ownership

- GIVEN the registry constructs a concrete strategy
- WHEN family-specific signal generation or parameter validity is evaluated
- THEN the concrete strategy module SHALL remain the owner of those semantics
- AND the registry SHALL NOT redefine backtest, ranking, policy, artifact, report, or signal-generation behavior

### Requirement: Strategy registry owns parameter metadata

The strategy registry SHALL expose expected parameter-name metadata for every registered strategy family.
The strategy registry SHALL also be the canonical owner of validating parameter-grid keys against that metadata.

#### Scenario: search-space validation uses registry metadata

- GIVEN search-space validation receives a strategy family and parameter grid
- WHEN it determines expected, missing, or unexpected parameter names
- THEN it SHALL derive expected parameter names from the strategy registry
- AND it SHALL call registry-owned parameter-grid validation
- AND it SHALL NOT define a separate strategy-to-parameter-name mapping
- AND it SHALL NOT redefine missing-parameter or unexpected-parameter key validation logic

#### Scenario: registry rejects missing parameter keys

- GIVEN a registered strategy family receives a parameter grid missing required parameter names
- WHEN registry-owned parameter-grid validation runs
- THEN AlphaForge SHALL raise a clear error
- AND the error SHALL include the strategy name
- AND the error SHALL include the missing parameter names

#### Scenario: registry rejects unexpected parameter keys

- GIVEN a registered strategy family receives a parameter grid with unregistered parameter names
- WHEN registry-owned parameter-grid validation runs
- THEN AlphaForge SHALL raise a clear error
- AND the error SHALL include the strategy name
- AND the error SHALL include the unexpected parameter names

#### Scenario: train-window validation uses registry metadata

- GIVEN validate-search or walk-forward validation checks train segment length
- WHEN a registered family declares integer window-like parameters
- THEN train-window validation SHALL derive those parameter names from the registry
- AND it SHALL reject train segments that are shorter than the largest requested integer window-like value

### Requirement: Scope remains registry-boundary only

This change SHALL NOT introduce GA search, parallel strategy execution, paper parsing, plugin loading, dynamic third-party strategy discovery, categorical parameter search, new strategy families, new CLI behavior, new artifact schema, new ranking behavior, new research policy behavior, new permutation behavior, new strategy construction behavior, or a new logging framework.

#### Scenario: schemas remain passive

- GIVEN schema dataclasses represent strategy-family search configs
- WHEN parameter-grid validation ownership is centralized
- THEN `schemas.py` SHALL remain a passive data-contract module
- AND `schemas.py` SHALL NOT import `strategy_registry.py`
- AND `StrategyFamilySearchConfig` and `StrategyComparisonConfig` SHALL NOT add registry-backed `__post_init__` validation

#### Scenario: current behavior remains unchanged for valid grids

- GIVEN existing workflows run for valid `ma_crossover` or `breakout` parameter grids
- WHEN registry-owned parameter-grid validation is introduced
- THEN existing CLI commands, artifact paths, JSON field names, CSV column names, ranking logic, validation logic, policy verdicts, permutation behavior, and strategy comparison output shape SHALL remain unchanged

### Requirement: Strategy comparison validates family grids before expensive execution

Strategy comparison workflow validation SHALL validate every `StrategyFamilySearchConfig` through the registry before expensive per-family validation, search, permutation, or artifact work begins.

#### Scenario: invalid comparison grid fails early

- GIVEN a strategy comparison config contains an invalid strategy-family parameter grid
- WHEN comparison workflow validation runs
- THEN the workflow SHALL fail before loading/running full validation, search, permutation, or artifact persistence work for that family
- AND the failure SHALL come from registry-owned parameter-grid validation

