# cli-request-assembly-boundary Specification

## Purpose

Define the canonical CLI request-assembly and dispatch boundary, including command parsing, workflow selection, and presentation-only payload formatting.

## MODIFIED Requirements

### Requirement: `cli.py` is the canonical owner of CLI request assembly and workflow dispatch

`src/alphaforge/cli.py` SHALL be the single authoritative owner of AlphaForge CLI argument parsing, command surface definition, request-shape assembly, workflow dispatch selection, and terminal output formatting.

#### Scenario: CLI parses and dispatches without owning domain semantics

- GIVEN a user invokes `alphaforge run --data sample.csv --short-window 5 --long-window 20`
- WHEN `cli.py` parses the command
- THEN it SHALL assemble the request DTOs needed for downstream execution
- AND it SHALL NOT decide the execution timing, market-data acceptance, or metric formulas itself

## ADDED Requirements

### Requirement: `research-validate` may accept a signal-file path for `custom_signal`

`cli.py` MAY accept `--signal-file` on `research-validate` when `--strategy custom_signal` is selected, and it SHALL pass that path through as request-shape data only.

#### Scenario: CLI assembles a custom-signal research-validation request

- GIVEN a user invokes `alphaforge research-validate --strategy custom_signal --signal-file path/to/signal.csv`
- WHEN `cli.py` parses the command
- THEN it SHALL assemble the request DTO with the signal-file path
- AND it SHALL NOT inspect the signal file contents
- AND it SHALL NOT compute `signal_value`
- AND it SHALL NOT import SignalForge internals
