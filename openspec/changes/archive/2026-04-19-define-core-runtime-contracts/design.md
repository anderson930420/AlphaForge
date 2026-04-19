# Design: define-core-runtime-contracts

## Canonical ownership mapping

- `src/alphaforge/config.py`
  - Keep literal defaults and raw policy constants only.
  - No validation logic, no execution semantics, no artifact rules.
- `src/alphaforge/data_loader.py`
  - Canonical market-data validator and normalizer.
  - Produces the cleaned OHLCV frame that downstream layers may trust.
- `src/alphaforge/schemas.py`
  - Runtime dataclass and shared type-alias owner.
  - No persistence-only column contract lists.
- `src/alphaforge/backtest.py`
  - Canonical execution law and runtime equity-curve / trade-log schema owner.
  - The backtest output contract lives here, not in `schemas.py`.
- `src/alphaforge/metrics.py`
  - Strategy metric formulas only.
- `src/alphaforge/benchmark.py`
  - Buy-and-hold curve construction, benchmark summary formulas, and benchmark normalization.
- `src/alphaforge/visualization.py`
  - Figure-only ownership.
  - Display-only derivations such as drawdown series remain here.
- `src/alphaforge/report.py`
  - Presentation-only ownership.
  - Consumes explicit report inputs and explicit artifact refs.
- `src/alphaforge/storage.py`
  - Persistence-only ownership.
  - Owns persisted artifact schema, filenames, output directories, and receipts.
- `src/alphaforge/experiment_runner.py`
  - Orchestration-only ownership.
  - Composes canonical contracts into workflow outputs but does not author them.
- `src/alphaforge/cli.py`
  - Command payload assembly only.
  - Serializes explicit runtime / persistence outputs without inferring contracts.

## Contract migration plan

- Move the backtest runtime equity-curve required column list out of `schemas.py` and into `backtest.py`.
- Keep `schemas.py` as the owner of dataclasses and aliases only.
- Update `backtest.py` docstrings to spell out:
  - next-bar target-position semantics
  - close-to-close return calculation
  - turnover, fee, slippage, and compounding rules
  - end-of-sample trade closeout
- Update `strategy.base.py` and `strategy/ma_crossover.py` docstrings to say the generated signal is a target position for the next tradable interval and is long-flat only in the MVP.
- Keep `metrics.py` and `benchmark.py` formulas where they already live, but tighten their module docstrings so no other module is treated as a hidden formula owner.
- Keep `report.py`, `visualization.py`, `storage.py`, `experiment_runner.py`, and `cli.py` on explicit input contracts only.

## Duplicate logic removal plan

- Remove the backtest equity-curve required column constant from `schemas.py`.
- Define the runtime equity-curve required column constant in `backtest.py` so the execution law owns the runtime frame contract.
- Keep the presentation-only required columns in `visualization.py`; those are a separate contract and should not be collapsed into the backtest runtime contract.
- Do not add a second canonical definition of strategy metrics or benchmark metrics in report or visualization code.
- Do not duplicate file-layout knowledge in CLI or report code when explicit artifact paths are already available.

## Verification plan

- Add an invariant test in `tests/test_backtest.py` that asserts the runtime equity curve exposes the canonical execution columns and that the trade log contract is stable.
- Keep the existing strategy test that proves the MA crossover emits long-flat signals.
- Keep the existing data-loader tests that prove sorting, duplicate resolution, and missing-data handling remain authoritative there.
- Keep the existing metrics and benchmark tests, and add only narrowly scoped assertions if a formula boundary needs reinforcement.
- Search the repository for the moved runtime column constant to prove there is exactly one canonical definition after migration.

## Temporary migration states

- No long-lived duplication is expected.
- The backtest runtime column contract should move in one step from `schemas.py` to `backtest.py`.
- If a short compatibility alias is needed during implementation, it must be deleted before the change is archived and must never be treated as the canonical owner.

