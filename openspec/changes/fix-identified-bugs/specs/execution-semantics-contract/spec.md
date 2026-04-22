# Delta for Execution Semantics Contract

## ADDED Requirements

### Requirement: trade extraction semantics remain backtest-owned even when the implementation is vectorized

`src/alphaforge/backtest.py` SHALL preserve the canonical long-flat trade extraction semantics when `_extract_trades()` is implemented through vectorized pandas operations.

#### Purpose

- Keep the execution owner authoritative even if the implementation changes from a row loop to vectorized frame operations.
- Prevent performance work from changing trade-boundary behavior, trade-log shape, or forced-exit semantics.

#### Canonical owner

- `src/alphaforge/backtest.py` remains the authoritative owner of realized-position transition semantics and trade-log construction.
- `src/alphaforge/metrics.py`, `src/alphaforge/storage.py`, `src/alphaforge/report.py`, and `src/alphaforge/cli.py` remain downstream consumers only.

#### Allowed responsibilities

- `backtest.py` MAY detect entries from realized-position transitions where the previous executed position is `0.0` and the current executed position is greater than `0.0`.
- `backtest.py` MAY detect exits from realized-position transitions where the previous executed position is greater than `0.0` and the current executed position is `0.0`.
- `backtest.py` MAY force-close an open long trade on the final row exactly as the current execution contract does.
- `backtest.py` MAY use vectorized pandas masks, shifts, cumulative identifiers, and grouped aggregations to realize that contract.

#### Explicit non-responsibilities

- No downstream module may recompute trade boundaries because the implementation became vectorized.
- `schemas.py` MUST NOT become the owner of trade extraction semantics or runtime trade-log rules.
- Performance optimizations MUST NOT change `TradeRecord` fields or the `BACKTEST_TRADE_LOG_COLUMNS` contract.

#### Inputs / outputs / contracts

- Inputs:
  - executed `position`
  - `close`
  - `strategy_return`
  - `datetime`
- Output:
  - a trade log whose rows still map to `TradeRecord`
- Contract rules:
  - empty frames return an empty trade log with stable columns
  - always-flat frames return an empty trade log
  - always-in-position frames produce one forced final-row exit
  - final-row forced exits match the current entry/exit time and PnL semantics

#### Invariants

- Entry detection remains `0 -> positive`.
- Exit detection remains `positive -> 0`.
- Final-row forced exit remains mandatory for open long trades.
- Trade-log shape and column names remain unchanged.

#### Scenario: vectorized trade extraction preserves a forced final-row exit

- GIVEN the final executed position is still positive
- WHEN `_extract_trades()` builds the trade log
- THEN it SHALL emit a closing trade record on the final row
- AND that forced exit SHALL use the final row's timestamp and close price
