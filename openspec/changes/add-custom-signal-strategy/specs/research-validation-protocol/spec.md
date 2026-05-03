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

### Requirement: Development research uses development data only

The runtime research validation workflow MUST run development-period search, development-period walk-forward validation, scoring-based candidate selection, and optional permutation diagnostics using only the development frame produced by the protocol split.

#### Scenario: development evidence excludes holdout rows

- GIVEN the workflow has split development and final holdout frames
- WHEN it runs search, walk-forward validation, or optional permutation diagnostics
- THEN those development evidence workflows MUST receive only development-frame rows
- AND they MUST NOT receive final holdout rows
- AND candidate selection MUST be based only on development-period search evidence

### Requirement: Pre-holdout decisions are frozen before final holdout evaluation

The frozen plan MUST include strategy family, selected parameters, parameter selection rule, scoring formula name, transaction cost assumptions, development period, holdout period, search space size, tried strategy families, tried parameter combinations, walk-forward configuration, and permutation configuration when enabled.

#### Scenario: frozen plan is recorded before holdout evaluation

- GIVEN development-period search and walk-forward evidence have completed
- WHEN the workflow prepares final holdout evaluation
- THEN it MUST record the frozen selected strategy family and selected parameters
- AND it MUST record the selection rule and scoring formula name used for development selection
- AND it MUST record transaction cost assumptions, periods, search breadth, walk-forward configuration, and permutation configuration when available
- AND final holdout evaluation MUST use the frozen selected candidate without rerunning parameter search on holdout data

### Requirement: Final holdout is evaluated once for research decisions and never used for tuning

The runtime research validation workflow MUST evaluate final holdout data using only the frozen selected candidate and frozen plan.

#### Scenario: custom-signal holdout uses the validated external target positions

- GIVEN the frozen selected candidate is `custom_signal`
- WHEN final holdout evaluation runs
- THEN the workflow MUST use the validated external target positions derived from the signal file
- AND it MUST NOT regenerate signals inside AlphaForge
- AND it MUST keep using the existing legacy close-to-close lagged execution semantics

### Requirement: Final reports disclose research process evidence and search breadth

The runtime research validation workflow MUST produce or expose a protocol summary that clearly separates development evidence, walk-forward development-period out-of-sample evidence, optional permutation diagnostic evidence, frozen plan, and final holdout result.

#### Scenario: protocol summary labels development OOS and final holdout separately

- GIVEN the research validation workflow completes
- WHEN the protocol summary is returned or persisted
- THEN walk-forward evidence MUST be labeled as development-period OOS evidence
- AND final holdout metrics MUST be labeled as final holdout evidence
- AND the summary MUST include search-space size, tried strategy family count, tried parameter combination count, transaction cost assumptions, frozen plan, and artifact references when persisted

### Requirement: Protocol scope excludes lower-level execution, data, strategy, storage, CLI, and rendering ownership

The runtime research validation workflow MUST coordinate existing data loading, search, walk-forward, permutation, final candidate evaluation, and storage concepts without redefining lower-level ownership.

#### Scenario: workflow delegates lower-level semantics

- GIVEN the research validation workflow runs
- WHEN it loads data, executes backtests, generates strategy signals, computes metrics, persists artifacts, parses CLI arguments, or renders reports
- THEN it MUST delegate to the existing canonical owners for those concerns
- AND it MUST NOT modify backtest execution semantics
- AND it MUST NOT redefine market data schema or strategy signal generation
- AND it MUST NOT implement report rendering
- AND it MUST NOT put storage-owned artifact schema in CLI code

### Requirement: `research-validate` accepts a custom-signal input contract without owning it

The workflow MAY accept an external signal-file path for `custom_signal`, but the signal-file contract itself MUST remain owned by the custom-signal boundary.

#### Scenario: workflow accepts the signal file path and defers validation

- GIVEN the CLI or a programmatic caller supplies a signal-file path
- WHEN the workflow enters the custom-signal branch
- THEN the workflow SHALL pass the path to the custom-signal boundary
- AND it SHALL NOT inspect file contents beyond orchestration needs
