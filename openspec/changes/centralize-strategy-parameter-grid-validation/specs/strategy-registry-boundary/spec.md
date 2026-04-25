# strategy-registry-boundary Specification

## Purpose

Tighten the strategy registry boundary so parameter-grid key validation is owned by the same module that owns expected parameter-name metadata.

## MODIFIED Requirements

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

### Requirement: Strategy comparison validates family grids before expensive execution

Strategy comparison workflow validation SHALL validate every `StrategyFamilySearchConfig` through the registry before expensive per-family validation, search, permutation, or artifact work begins.

#### Scenario: invalid comparison grid fails early

- GIVEN a strategy comparison config contains an invalid strategy-family parameter grid
- WHEN comparison workflow validation runs
- THEN the workflow SHALL fail before loading/running full validation, search, permutation, or artifact persistence work for that family
- AND the failure SHALL come from registry-owned parameter-grid validation

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
