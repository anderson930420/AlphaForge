# strategy-registry-boundary Specification

## Purpose

Tighten the strategy registry boundary so family registration can include validation-only custom-signal workflows without making the registry a signal-file parser or signal-value generator.

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

## ADDED Requirements

### Requirement: Strategy registry may register validation-only custom-signal workflows

The strategy registry SHALL be able to register `custom_signal` as a workflow-dispatch family, but it SHALL NOT compute signal values or parse external signal files.

#### Scenario: custom_signal remains registry-visible but signal-owned

- GIVEN the `custom_signal` workflow is available to research validation
- WHEN the strategy registry exposes family metadata
- THEN it SHALL include `custom_signal`
- AND it SHALL NOT infer or compute `signal_value`
- AND it SHALL NOT parse `signal.csv`
- AND it SHALL NOT own the binary-to-target mapping
