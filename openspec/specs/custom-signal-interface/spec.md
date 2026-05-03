# custom-signal-interface Specification

## Purpose
TBD - created by archiving change add-custom-signal-strategy. Update Purpose after archive.
## Requirements
### Requirement: External signal-file validation and target-position derivation are custom-signal owned

`src/alphaforge/custom_signal.py` SHALL own validation of externally supplied `signal.csv` files and derivation of `target_position = float(signal_binary)` for the `custom_signal` workflow.

#### Scenario: custom-signal validation has one canonical owner

- GIVEN AlphaForge consumes an external `signal.csv`
- WHEN the `custom_signal` workflow validates the file
- THEN `custom_signal.py` SHALL own the validation and target-position derivation
- AND no other module SHALL redefine the signal-file contract or binary-to-target mapping

