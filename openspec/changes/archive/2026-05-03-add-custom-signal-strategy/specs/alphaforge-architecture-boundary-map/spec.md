# AlphaForge Architecture Boundary Map Specification

## Purpose

- Define the authoritative boundary map for AlphaForge so every business rule, execution semantic, schema, naming convention, and workflow responsibility has exactly one canonical owner.

## MODIFIED Requirements

### Requirement: AlphaForge modules shall have exactly one canonical owner per boundary

AlphaForge SHALL assign each business rule, execution semantic, schema, naming convention, and workflow responsibility to exactly one canonical owner, with lower-level capability specs allowed to refine but not contradict the top-level map.

#### Scenario: Boundary ownership remains single-sourced

- **WHEN** a maintainer looks up the owner for market data, execution, persistence, reporting, CLI dispatch, or orchestration
- **THEN** the architecture boundary map SHALL provide a single canonical answer
- **AND** lower-level specs SHALL only refine that answer, not create a competing one

## ADDED Requirements

### Requirement: `custom_signal.py` owns external signal-file validation and target-position derivation

`src/alphaforge/custom_signal.py` SHALL be the canonical owner of validating externally supplied `signal.csv` files and deriving `target_position` values for the `custom_signal` workflow.

#### Scenario: custom signal validation has one canonical owner

- GIVEN AlphaForge consumes an external `signal.csv`
- WHEN the `custom_signal` workflow validates the file
- THEN `custom_signal.py` SHALL own the validation and target-position derivation
- AND no other module SHALL redefine the signal-file contract or binary-to-target mapping

## Allowed responsibilities

### A. Layer map

- Domain implementation layer:
  - `src/alphaforge/custom_signal.py` is authoritative for external signal-file validation and target-position derivation for the `custom_signal` workflow.

### B. Canonical truth table

| Canonical truth category | Authoritative owner | Layer role | Non-authoritative consumers |
| --- | --- | --- | --- |
| External signal-file validation and binary-to-target mapping | `src/alphaforge/custom_signal.py` | contract-enforcement + implementation | `runner_workflows.py`, `cli.py`, `strategy_registry.py`, `backtest.py` |

### C. Explicit non-responsibilities

- `custom_signal.py` must not own execution semantics, market-data acceptance semantics, search-space generation, ranking logic, or report rendering.

## Cross-module dependencies

- `custom_signal.py` depends on accepted market data from `data_loader.py` for date alignment.
- `runner_workflows.py` may consume validated target positions from `custom_signal.py`.
- `backtest.py` consumes target positions and remains the execution owner.
- `cli.py` may surface a signal-file path but must not interpret signal contents.
- `strategy_registry.py` may register the `custom_signal` family but must not compute signal values.
