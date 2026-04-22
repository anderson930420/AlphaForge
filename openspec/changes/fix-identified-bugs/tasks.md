# Tasks

## 1. Spec and contract alignment

- [x] 1.1 Add the OpenSpec proposal and boundary deltas for execution trade extraction, permutation family support, CLI permutation request assembly, and per-period Sharpe semantics.
- [x] 1.2 Confirm the code changes stay within the existing owners: `scoring.py`, `backtest.py`, `permutation.py`, `cli.py`, and `metrics.py`, with `schemas.py` unchanged.

## 2. Code migration

- [x] 2.1 Fix the missing `Any` import in `src/alphaforge/scoring.py`.
- [x] 2.2 Rewrite `src/alphaforge/backtest.py:_extract_trades()` with vectorized pandas operations while preserving current trade-log semantics and output columns.
- [x] 2.3 Extend `src/alphaforge/permutation.py` to support both `ma_crossover` and `breakout`, returning the shared `Strategy` type and deriving supported families from `src/alphaforge/search.py`.
- [x] 2.4 Update `src/alphaforge/cli.py` so `permutation-test` accepts `--strategy` and passes the selected `strategy_name` and fixed parameters through correctly.
- [x] 2.5 Update `src/alphaforge/metrics.py` so Sharpe subtracts an optional per-period `risk_free_rate` with a backward-compatible default of `0.0`.

## 3. Verification

- [x] 3.1 Add or update backtest tests for empty, always-flat, always-in-position, forced-final-exit, and standard entry/exit scenarios.
- [x] 3.2 Add or update permutation and CLI tests for breakout support and family-aware `permutation-test` request assembly.
- [x] 3.3 Add or update metric tests for default and non-zero per-period `risk_free_rate` Sharpe behavior.
- [x] 3.4 Run `pytest` and confirm the requested four-bug change passes without unrelated refactors.

## 4. Cleanup

- [x] 4.1 Remove any now-redundant MA-only diagnostic wiring once the family-aware path is in place.
- [x] 4.2 Log each meaningful implementation step through the local Obsidian workflow and leave this task list fully completed when the change is done.
