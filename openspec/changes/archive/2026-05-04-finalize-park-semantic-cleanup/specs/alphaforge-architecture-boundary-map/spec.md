# Delta for AlphaForge Architecture Boundary Map Cleanup

## ADDED Requirements

### Requirement: AlphaForge is a validation engine, not the alpha-generation platform

AlphaForge SHALL be documented and treated as a spec-driven quant research validation engine and SHALL NOT be positioned as the primary alpha-generation platform.

#### Scenario: AlphaForge boundary statements remain validation-focused

- GIVEN future documentation or canonical boundary text describes AlphaForge
- WHEN it states the repo's purpose
- THEN it SHALL describe AlphaForge as a validation layer for OHLCV research, backtesting, diagnostics, and externally generated signals
- AND it SHALL NOT claim AlphaForge is the signal-generation owner

#### Scenario: SignalForge remains the alpha-generation owner

- GIVEN a signal package is produced for AlphaForge
- WHEN the package handoff is described
- THEN SignalForge SHALL be the signal-generation owner
- AND AlphaForge SHALL remain the validator and backtester of that exported signal package

