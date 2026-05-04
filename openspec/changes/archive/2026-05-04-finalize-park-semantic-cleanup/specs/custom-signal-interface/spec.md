# Delta for Custom Signal Interface Cleanup

## MODIFIED Requirements

### Requirement: External signal-file validation and target-position derivation are custom-signal owned

`src/alphaforge/custom_signal.py` SHALL own validation of externally supplied `signal.csv` files and derivation of `target_position = float(signal_binary)` for the `custom_signal` workflow.

#### Scenario: custom-signal validation has one canonical owner

- GIVEN AlphaForge consumes an external `signal.csv`
- WHEN the `custom_signal` workflow validates the file
- THEN `custom_signal.py` SHALL own the validation and target-position derivation
- AND no other module SHALL redefine the signal-file contract or binary-to-target mapping

## ADDED Requirements

### Requirement: custom_signal input schema is explicit

AlphaForge SHALL treat external `signal.csv` files for `custom_signal` as seven-column inputs with the canonical column order:

- `datetime`
- `available_at`
- `symbol`
- `signal_name`
- `signal_value`
- `signal_binary`
- `source`

#### Scenario: schema validation rejects missing required columns

- GIVEN an external signal file missing one or more required columns
- WHEN `custom_signal.py` validates the file
- THEN validation SHALL fail clearly

### Requirement: signal_binary is the only execution input

AlphaForge SHALL derive execution target positions from `signal_binary` only and SHALL ignore `signal_value` for execution.

#### Scenario: signal_value is schema-only

- GIVEN a valid external signal row with `signal_value`
- WHEN AlphaForge prepares execution input
- THEN `signal_value` SHALL NOT be used to derive `target_position`
- AND `target_position` SHALL equal `float(signal_binary)`

### Requirement: custom_signal temporal and uniqueness rules are strict

AlphaForge SHALL require `available_at <= datetime`, SHALL reject duplicate `datetime` rows for the same symbol, and SHALL require signal dates to align exactly with the market-data dates provided to AlphaForge.

#### Scenario: duplicate or misaligned signals fail

- GIVEN a signal file with duplicate datetime rows for the same symbol
- OR a signal file whose dates do not match the market data dates
- WHEN AlphaForge validates the signal file
- THEN validation SHALL fail

### Requirement: custom_signal uses the legacy close-to-close lagged execution semantics

The `custom_signal` workflow SHALL use `legacy_close_to_close_lagged` execution semantics and SHALL NOT introduce a second execution model.

#### Scenario: custom_signal executes through the canonical backtest law

- GIVEN a validated external `signal.csv`
- WHEN AlphaForge executes the `custom_signal` workflow
- THEN the runtime position SHALL use the canonical lagged close-to-close backtest law

### Requirement: custom_signal does not depend on SignalForge internals

AlphaForge SHALL validate and execute externally generated signal files without importing SignalForge internals or taking a dependency on SignalForge runtime packages.

#### Scenario: import boundaries remain external

- GIVEN AlphaForge validates a custom-signal package
- WHEN the implementation loads the external signal file
- THEN it SHALL not import SignalForge internals
- AND it SHALL not require SignalForge as a dependency

