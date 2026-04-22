# Proposal: vectorize-trade-gross-return

## Boundary problem

- `src/alphaforge/backtest.py` owns trade extraction semantics, but `_extract_trades()` still computes `gross_return` with `DataFrame.apply(axis=1)`, which is row-by-row Python execution.

## Canonical ownership decision

- `src/alphaforge/backtest.py` remains the only owner of trade extraction behavior and runtime trade-log field semantics.
- The implementation detail for `gross_return` is updated to vectorized column arithmetic without changing ownership or output contract.

## Scope

- Update `_extract_trades()` in `src/alphaforge/backtest.py` to remove `apply(axis=1)` from `gross_return` computation.
- Keep semantics unchanged for zero `entry_price` rows by preserving `gross_return = 0.0` in that case.

## Migration risk

- Low risk: formula and fields stay the same, but vectorized expression must preserve the zero-entry-price guard semantics from the previous lambda path.

## Acceptance conditions

- `_extract_trades()` has no `apply(axis=1)` call for `gross_return`.
- `gross_return` values remain consistent with prior behavior, including zero `entry_price` handling.
- Backtest tests pass.
