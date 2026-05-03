# research-validation-protocol Specification

## Purpose

TBD - created by archiving change formalize-research-validation-protocol. Update Purpose after archive.

## Requirements

### Requirement: Multi-year research data is split into development and final holdout periods

AlphaForge MUST provide a runtime research validation workflow that loads canonical multi-year OHLCV data and splits it into explicit development and final holdout periods before any protocol-governed research evidence is generated.

## ADDED Requirements

### Requirement: External signal-backed custom-signal validation is protocol-owned and file-driven

The runtime research validation workflow MUST support a `custom_signal` path that validates an external `signal.csv` file before final candidate evaluation.

The workflow MUST delegate signal-file validation and target-position derivation to the custom-signal boundary and MUST NOT compute signal values internally.

#### Scenario: custom-signal workflow consumes external signals without generating them

- GIVEN a caller runs `alphaforge research-validate --strategy custom_signal --signal-file ...`
- WHEN the workflow prepares the candidate
- THEN AlphaForge MUST validate the external signal file through the custom-signal boundary
- AND it MUST derive target positions from `signal_binary`
- AND it MUST ignore `signal_value` for execution
- AND it MUST NOT import SignalForge internals

#### Scenario: signal dates are aligned with market data before evidence generation

- GIVEN the workflow has accepted market data and an external signal file
- WHEN the workflow validates `custom_signal`
- THEN signal dates MUST align with the market-data dates
- AND duplicate `datetime` values for the same `symbol` MUST fail
- AND missing signal dates MUST fail by default
- AND `available_at` MUST be less than or equal to `datetime`

### Requirement: `research-validate` accepts a custom-signal input contract without owning it

The workflow MAY accept an external signal-file path for `custom_signal`, but the signal-file contract itself MUST remain owned by the custom-signal boundary.

#### Scenario: workflow accepts the signal file path and defers validation

- GIVEN the CLI or a programmatic caller supplies a signal-file path
- WHEN the workflow enters the custom-signal branch
- THEN the workflow SHALL pass the path to the custom-signal boundary
- AND it SHALL NOT inspect file contents beyond orchestration needs
