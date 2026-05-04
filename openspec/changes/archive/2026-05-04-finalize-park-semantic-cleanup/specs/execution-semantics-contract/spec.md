# Delta for Execution Semantics Contract Cleanup

## MODIFIED Requirements

### Requirement: trade logs are return-based and must not be labeled as dollar PnL

`src/alphaforge/backtest.py` SHALL own a return-based trade-log contract whose fields describe returns and holding periods, not dollar accounting.

#### Allowed responsibilities

- `backtest.py` MAY emit the canonical trade-log fields:
  - `entry_datetime`
  - `exit_datetime`
  - `entry_price`
  - `exit_price`
  - `holding_period`
  - `trade_gross_return`
  - `trade_net_return`
  - `cost_return_contribution`
  - `entry_target_position`
  - `exit_target_position`
- `backtest.py` MAY define `holding_period` as the integer count of bars between entry and exit on the executed-position timeline.
- `backtest.py` MAY define `trade_net_return` as `trade_gross_return - cost_return_contribution`.

#### Explicit non-responsibilities

- `backtest.py` MUST NOT label the canonical trade contribution as dollar PnL.
- `backtest.py` MUST NOT require shares-level accounting, partial fills, multi-leg trades, or broker-like accounting in this change.
- `backtest.py` MUST NOT expose the canonical trade log as a dollar ledger.
- `storage.py`, `report.py`, and `cli.py` MUST NOT rename the canonical trade contribution back into `net_pnl` or similar dollar-PnL terminology.

#### Inputs / outputs / contracts

- Inputs:
  - realized executed positions from the backtest
  - entry and exit prices from the market data
  - transaction-cost contributions from the backtest execution law
- Outputs:
  - a return-based trade log with the canonical fields listed above
- Contract rules:
  - `trade_gross_return` and `trade_net_return` are return values, not dollar values
  - `cost_return_contribution` is the return-space effect of transaction costs
  - canonical trade-log fields must be persisted under the storage-owned `trade_log.csv` schema

#### Invariants

- Trade log semantics remain return-based.
- Dollar PnL terminology is not part of the canonical trade log.
- `trade_net_return` is the value used by downstream win-rate logic.
- A zero-trade result remains representable without inventing pseudo-accounting fields.

#### Scenario: trade log uses return terminology only

- GIVEN a future persisted trade log
- WHEN the schema is emitted or reviewed
- THEN the fields SHALL be the return-based fields listed above
- AND the canonical schema SHALL NOT use `net_pnl` or other dollar-PnL labels

