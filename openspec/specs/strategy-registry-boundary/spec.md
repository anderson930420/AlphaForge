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

#### Scenario: search-space validation uses registry metadata

- GIVEN search-space validation receives a strategy family and parameter grid
- WHEN it determines expected, missing, or unexpected parameter names
- THEN it SHALL derive expected parameter names from the strategy registry
- AND it SHALL NOT define a separate strategy-to-parameter-name mapping

#### Scenario: train-window validation uses registry metadata

- GIVEN validate-search or walk-forward validation checks train segment length
- WHEN a registered family declares integer window-like parameters
- THEN train-window validation SHALL derive those parameter names from the registry
- AND it SHALL reject train segments that are shorter than the largest requested integer window-like value

### Requirement: Scope remains registry-boundary only

This change SHALL NOT introduce GA search, parallel strategy execution, paper parsing, plugin loading, dynamic third-party strategy discovery, categorical parameter search, new strategy families, new CLI behavior, new artifact schema, new ranking behavior, new research policy behavior, or a new logging framework.

#### Scenario: current behavior remains unchanged

- GIVEN existing workflows run for `ma_crossover` or `breakout`
- WHEN the registry boundary is introduced
- THEN existing CLI commands, artifact paths, JSON field names, CSV column names, ranking logic, validation logic, policy verdicts, and strategy comparison output shape SHALL remain unchanged

#### Scenario: future family additions use the registry boundary

- GIVEN a future strategy family is added
- WHEN it is introduced into AlphaForge
- THEN the primary ownership update SHALL be adding a registry registration plus strategy-specific tests
- AND search, runner, protocol, and permutation modules SHALL NOT require scattered new family ownership branches

