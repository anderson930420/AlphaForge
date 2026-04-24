# Tasks

## 1. OpenSpec

- [x] 1.1 Create proposal, design, tasks, and execution-semantics spec delta.
- [x] 1.2 Validate the OpenSpec change.

## 2. Implementation

- [x] 2.1 Inspect `backtest.py`, `schemas.py`, direct backtest tests, and callers.
- [x] 2.2 Add execution-owned target-position coercion and validation.
- [x] 2.3 Preserve existing lag, fee, slippage, turnover, trade extraction, and equity formulas.

## 3. Tests

- [x] 3.1 Add regression coverage for same-length `pd.Series` with mismatched index raising `ValueError`.
- [x] 3.2 Add coverage for matching-index `pd.Series` being accepted.
- [x] 3.3 Add coverage for list-like or numpy-like target positions being accepted positionally.
- [x] 3.4 Add coverage for length mismatch raising `ValueError`.

## 4. Verification

- [x] 4.1 Run `openspec validate stabilize-backtest-target-position-alignment --type change --no-interactive`.
- [x] 4.2 Run `pytest`.
- [x] 4.3 Log meaningful implementation and verification steps to Obsidian.
