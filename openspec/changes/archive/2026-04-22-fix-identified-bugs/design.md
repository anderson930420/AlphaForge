# Design: fix-identified-bugs

## Canonical ownership mapping

- `src/alphaforge/scoring.py`
  - keep ranking-key implementation details local
  - add the missing `Any` import without moving any contract into `schemas.py`
- `src/alphaforge/backtest.py`
  - keep ownership of trade extraction semantics
  - replace the Python row loop in `_extract_trades()` with vectorized transition masks and grouped trade aggregation
- `src/alphaforge/search.py`
  - remain the authoritative owner of `SUPPORTED_STRATEGY_FAMILIES`
- `src/alphaforge/permutation.py`
  - import `BreakoutStrategy`
  - derive supported family names from `search.py`
  - broaden `_build_strategy()` to return the shared `Strategy` type for MA crossover or breakout
- `src/alphaforge/cli.py`
  - expose `--strategy` on `permutation-test`
  - assemble the fixed `StrategySpec` through the same explicit family-selection pattern used by `run`, `search`, `validate-search`, and `walk-forward`
- `src/alphaforge/metrics.py`
  - keep ownership of Sharpe semantics
  - subtract a caller-supplied per-period `risk_free_rate` before standard deviation scaling
- tests under `tests/`
  - prove the vectorized trade extractor preserves current semantics
  - prove permutation diagnostics accept both supported families
  - prove CLI permutation request assembly follows the new strategy-selection contract
  - prove Sharpe stays backward compatible at `risk_free_rate=0.0` and changes when a non-zero per-period rate is passed

## Contract migration plan

- Bug 1:
  - add `from typing import Any` to `scoring.py`
  - keep the ranking-key annotation exactly where it already belongs
- Bug 2:
  - compute entry and exit masks from realized `position` transitions using `shift()`
  - treat a final still-open position as a synthetic exit on the last row while preserving the current output row values
  - derive each trade by pairing entry rows with exit rows and summing `strategy_return` over each trade id
  - return the same `TradeRecord` field set and `BACKTEST_TRADE_LOG_COLUMNS`
- Bug 3:
  - import `SUPPORTED_STRATEGY_FAMILIES` from `search.py` into `permutation.py` and `cli.py`
  - extend `_build_strategy()` with explicit branches for `ma_crossover` and `breakout`
  - add a family-aware CLI helper for permutation fixed-candidate assembly so `strategy_name` is passed through unchanged to the diagnostic owner
- Bug 4:
  - extend `_compute_sharpe_ratio()` and `compute_metrics()` with `risk_free_rate: float = 0.0`
  - compute Sharpe from `returns - risk_free_rate`, treating the input as already aligned to the per-period sampling frequency
  - leave all existing `MetricReport` field names and `BacktestConfig` unchanged

## Duplicate logic removal plan

- Remove the row-by-row Python loop from `_extract_trades()` once the vectorized trade-id path is in place.
- Remove the MA-only narrowing in `permutation.py` by returning `Strategy` instead of `MovingAverageCrossoverStrategy`.
- Remove the MA-only `StrategySpec(name=\"ma_crossover\", ...)` assembly in the `permutation-test` CLI branch and replace it with a family-aware helper.
- Avoid introducing any second supported-family list or any second Sharpe implementation outside `metrics.py`.

## Verification plan

- Add or update backtest tests for:
  - empty frame
  - always flat
  - always in position
  - final-row forced exit
  - standard entry/exit transitions
- Add or update permutation and CLI tests for:
  - breakout permutation execution support
  - `permutation-test --strategy breakout`
  - MA regression behavior for the existing permutation path
- Add or update metric tests for:
  - default backward-compatible Sharpe behavior at `risk_free_rate=0.0`
  - excess-return Sharpe behavior for a non-zero per-period `risk_free_rate`
- Run the full `pytest` suite after implementation.

## Temporary migration states

- No lasting temporary compatibility layer is expected.
- During implementation there may be a brief overlap where the new CLI helper exists before the old inline MA-only assembly is removed; the removal trigger is the passing permutation CLI test.
- `schemas.py` remains untouched unless implementation proves there is no other viable path, which is not expected for these four bugs.
