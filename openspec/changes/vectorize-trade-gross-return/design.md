# Design: vectorize-trade-gross-return

## Canonical ownership mapping

- `src/alphaforge/backtest.py` remains the single implementation owner for `_extract_trades()` and `gross_return` derivation.

## Contract migration plan

- Replace:
  - row-wise lambda on `trade_frame.apply(axis=1)`
- With:
  - vectorized division and subtraction on series columns
  - explicit zero-entry guard via temporary replacement/fill

## Duplicate logic removal plan

- Remove the residual row-by-row `apply(axis=1)` path for `gross_return`.

## Verification plan

- Run `pytest tests/test_backtest.py`.
- Run full `pytest` if needed to confirm no regressions.

## Temporary migration states

- None expected; this is a single-expression replacement.
