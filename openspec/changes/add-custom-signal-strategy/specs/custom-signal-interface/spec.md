# custom-signal-interface Specification

## Purpose

- Define the canonical boundary for validating externally supplied `signal.csv` files and converting them into AlphaForge target positions for the `custom_signal` workflow.
- Keep AlphaForge able to consume a precomputed signal file without computing signals internally.

## Canonical owner

- `src/alphaforge/custom_signal.py` is the authoritative owner of external signal-file validation and target-position derivation for the `custom_signal` workflow.

## ADDED Requirements

### Requirement: External signal-file validation and target-position derivation are custom-signal owned

`src/alphaforge/custom_signal.py` SHALL own validation of externally supplied `signal.csv` files and derivation of `target_position = float(signal_binary)` for the `custom_signal` workflow.

#### Scenario: custom-signal validation has one canonical owner

- GIVEN AlphaForge consumes an external `signal.csv`
- WHEN the `custom_signal` workflow validates the file
- THEN `custom_signal.py` SHALL own the validation and target-position derivation
- AND no other module SHALL redefine the signal-file contract or binary-to-target mapping

## Allowed responsibilities

- Validate the external `signal.csv` contract for `custom_signal`.
- Enforce required `signal.csv` columns and row-level checks.
- Derive `target_position` from `signal_binary` using the canonical mapping.
- Produce validated signal-derived inputs for runner workflows.
- Carry signal provenance fields such as `signal_name` and `source` forward as metadata when needed.

## Explicit non-responsibilities

- `custom_signal.py` MUST NOT compute `signal_value`.
- `custom_signal.py` MUST NOT import SignalForge internals or treat SignalForge as a runtime dependency.
- `custom_signal.py` MUST NOT own execution semantics, market-data acceptance semantics, metrics semantics, benchmark semantics, or persisted artifact layout.
- `custom_signal.py` MUST NOT own search-space generation or strategy-family ranking semantics.
- `custom_signal.py` MUST NOT own report rendering or CLI parsing.

## Inputs / outputs / contracts

- Inputs:
  - external `signal.csv` path or equivalent loaded frame
  - canonical market data accepted by `data_loader.py`
- Required `signal.csv` columns:
  - `datetime`
  - `available_at`
  - `symbol`
  - `signal_name`
  - `signal_value`
  - `signal_binary`
  - `source`
- Columns AlphaForge may use for execution:
  - `datetime`
  - `available_at`
  - `symbol`
  - `signal_name`
  - `signal_binary`
  - `source`
- Columns AlphaForge must not use for execution:
  - `signal_value`
- Outputs:
  - validated signal-derived target positions
  - validation metadata describing accepted or rejected rows
- Contract rules:
  - `target_position = float(signal_binary)`
  - `signal_binary` values must be binary `0` or `1`

## Invariants

- `datetime` and `available_at` are required for every row.
- `available_at <= datetime` for every row.
- `symbol` is required for every row.
- Duplicate `datetime` rows for the same `symbol` fail.
- Signal dates must align with accepted market-data dates.
- Missing signal dates fail by default.
- `signal_value` is ignored for execution.
- The custom-signal path uses the existing `legacy_close_to_close_lagged` execution semantics.

## Cross-module dependencies

- `data_loader.py` provides the accepted market-data frame used for date alignment.
- `runner_workflows.py` may orchestrate validated signal-derived target positions into execution.
- `backtest.py` remains the authoritative execution owner.
- `cli.py` may surface the signal-file path but must not inspect file contents.
- `strategy_registry.py` may register `custom_signal` for dispatch metadata only.

## Failure modes if this boundary is violated

- If `signal_value` is treated as executable truth, AlphaForge silently drifts from the intended external signal contract.
- If SignalForge internals are imported, AlphaForge gains an unwanted upstream dependency and the workflow stops being file-contract driven.
- If date alignment or duplicate rules are duplicated elsewhere, the same signal file can pass one path and fail another.
- If execution semantics are redefined here, the custom-signal path becomes a second execution owner.

## Migration notes from current implementation

- No canonical owner currently exists for external signal-file validation.
- `research-validate` currently lacks a dedicated external signal contract.
- This change introduces the new owner and makes the runner, CLI, and registry derive from it instead of validating signals independently.

## Open questions / deferred decisions

- Whether `custom_signal.py` should expose a reusable in-memory validation helper in addition to file loading is deferred.
- Whether future external-signal strategies will share this module or split into a broader signal-adapter boundary is deferred.
