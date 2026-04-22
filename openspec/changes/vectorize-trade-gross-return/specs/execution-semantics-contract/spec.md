# Delta for Execution Semantics Contract

## ADDED Requirements

### Requirement: trade-log gross-return computation is vectorized within the backtest owner

`src/alphaforge/backtest.py` SHALL compute trade-log `gross_return` using vectorized column operations rather than row-by-row `DataFrame.apply(axis=1)`.

#### Purpose

- Keep execution semantics in the canonical owner while removing residual row-wise Python execution in trade extraction.

#### Canonical owner

- `src/alphaforge/backtest.py` remains the authoritative owner of trade extraction and trade-log field computation.

#### Inputs / outputs / contracts

- Inputs:
  - `entry_price`
  - `exit_price`
- Output:
  - `gross_return`
- Contract rules:
  - `gross_return` equals `(exit_price / entry_price) - 1.0` when `entry_price` is non-zero
  - `gross_return` equals `0.0` when `entry_price` is zero
