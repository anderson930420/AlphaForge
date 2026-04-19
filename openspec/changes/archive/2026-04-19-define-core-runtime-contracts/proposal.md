# Proposal: define-core-runtime-contracts

## Boundary problem

- `src/alphaforge/schemas.py` still carries a backtest equity-curve column list even though `src/alphaforge/backtest.py` is the module that actually defines execution semantics and produces the runtime frame.
- `src/alphaforge/metrics.py`, `src/alphaforge/benchmark.py`, and `src/alphaforge/visualization.py` each touch drawdown-adjacent logic, but the current codebase does not yet make the ownership boundary explicit enough to prevent drift.
- `src/alphaforge/report.py`, `src/alphaforge/storage.py`, `src/alphaforge/experiment_runner.py`, and `src/alphaforge/cli.py` already consume explicit contracts in several places, but the canonical runtime contract is still not frozen as a first-class source of truth.
- `src/alphaforge/config.py` currently mixes literal defaults with policy text that is consumed by loading and execution code, which makes it easy to confuse constants with authority.

## Canonical ownership decision

- `src/alphaforge/config.py` becomes the single authoritative owner of literal defaults, ranges, aliases, and input-policy constants only.
- `src/alphaforge/data_loader.py` becomes the single authoritative owner of market-data validation and normalization.
- `src/alphaforge/schemas.py` remains the authoritative owner of in-memory dataclasses and shared type aliases only.
- `src/alphaforge/backtest.py` becomes the single authoritative owner of execution semantics and the canonical minimum runtime equity-curve / trade-log contract.
- `src/alphaforge/metrics.py` becomes the single authoritative owner of strategy metric formulas.
- `src/alphaforge/benchmark.py` becomes the single authoritative owner of benchmark curve construction and benchmark summary formulas.
- `src/alphaforge/visualization.py` remains the authoritative owner of figure-only contracts and display-only derived series.
- `src/alphaforge/report.py` remains presentation-only and must consume explicit runtime and presentation inputs.
- `src/alphaforge/storage.py` remains persistence-only and owns persisted artifact schemas, filenames, and layout.
- `src/alphaforge/experiment_runner.py` remains orchestration-only.
- `src/alphaforge/cli.py` remains command payload assembly only.

## Scope

- Market data canonical schema:
  - required OHLCV columns
  - sort order
  - duplicate-row policy
  - missing-data policy boundary
  - validation ownership versus downstream consumption
- Strategy signal contract:
  - `generate_signals()` return type
  - next-bar versus same-bar meaning
  - current MVP value range
  - long-flat-only formal boundary
- Backtest execution semantics:
  - position lag rule
  - close-to-close return definition
  - turnover definition
  - fee and slippage application
  - equity compounding
  - end-of-sample trade closeout
  - canonical runtime output columns
- Metric and benchmark ownership:
  - Sharpe ratio
  - max drawdown
  - turnover
  - win rate
  - benchmark total return
  - benchmark max drawdown
- Artifact layering:
  - minimum runtime artifact contract
  - enriched presentation contract
  - persisted artifact contract

## Migration risk

- Any backtest-runtime contract change can break tests that implicitly relied on undocumented column order or implicit frame shape.
- Removing the runtime equity-curve column list from `schemas.py` can break callers that incorrectly treated schema definitions as runtime truth.
- Tightening ownership boundaries may require docstring and test updates in `backtest.py`, `metrics.py`, `benchmark.py`, `visualization.py`, `report.py`, `storage.py`, `experiment_runner.py`, and `cli.py`.
- Persisted JSON and CSV outputs should remain behaviorally stable, but the contract source that defines them must become unambiguous.

## Acceptance conditions

- There is one clearly documented source of truth for core runtime behavior.
- The formal backtest semantics are explicit and testable.
- The canonical minimum runtime artifact contract is separate from enriched report/view contracts.
- Metric and benchmark ownership are explicit and non-overlapping.
- `report.py` is explicitly presentation-only.
- `visualization.py` is explicitly figure-only.
- `storage.py` is explicitly persistence-only.
- `experiment_runner.py` is explicitly orchestration-only.
- There is no obvious duplicated runtime field-contract definition that can silently drift between `schemas.py` and `backtest.py`.
- The resulting spec makes runner decomposition safer and simpler.

## Follow-up changes

- `decompose-experiment-runner-orchestration`
- `normalize-persistence-artifact-contracts`

