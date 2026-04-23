# Tasks

## 1. Spec and contract alignment

- [x] 1.1 Add change artifacts documenting the vectorization-only bug fix for trade-log `gross_return`.

## 2. Code migration

- [x] 2.1 Replace row-by-row `apply(axis=1)` in `_extract_trades()` with vectorized gross-return column math.

## 3. Verification

- [x] 3.1 Run targeted backtest tests to confirm behavior is unchanged.

## 4. Cleanup

- [x] 4.1 Log meaningful implementation steps through the local Obsidian workflow.
