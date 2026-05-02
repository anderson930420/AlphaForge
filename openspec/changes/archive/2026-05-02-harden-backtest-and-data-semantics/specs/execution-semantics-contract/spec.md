# Delta for Execution Semantics Contract

## ADDED Requirements

### Requirement: `backtest.py` emits explicit legacy close-to-close lagged execution semantics metadata

`src/alphaforge/backtest.py` SHALL be the canonical owner of the current execution semantics contract and SHALL emit explicit metadata describing the legacy execution law used by AlphaForge.

#### Purpose

- Make the current execution law visible instead of leaving it implicit in runtime behavior.
- Prevent downstream modules from guessing whether AlphaForge uses next-open, MOC, intraday, shorting, leverage, or multi-asset execution.

#### Canonical owner

- `src/alphaforge/backtest.py` is the authoritative owner of execution semantics.
- `src/alphaforge/storage.py` may persist the emitted metadata as a derived artifact field.
- `src/alphaforge/report.py` may display the emitted metadata as presentation only.

#### Allowed responsibilities

- `backtest.py` MAY interpret `target_position[t]` as the strategy's desired position at bar `t`.
- `backtest.py` MAY realize `position[t]` as `target_position[t-1]`.
- `backtest.py` MAY compute `close_return[t]` from close-to-close bars.
- `backtest.py` MAY compute `strategy_return[t]` as `position[t] * close_return[t] - transaction_cost[t]`.
- `backtest.py` MAY clip positions into the supported long-only range `[0.0, 1.0]`.
- `backtest.py` MAY emit the following metadata fields in runtime summaries and persisted artifacts:
  - `execution_semantics = "legacy_close_to_close_lagged"`
  - `position_rule = "position[t] = target_position[t-1]"`
  - `return_rule = "close_to_close"`
  - `position_bounds = [0.0, 1.0]`
  - `supports_shorting = false`
  - `supports_leverage = false`

#### Explicit non-responsibilities

- `backtest.py` MUST NOT become a realistic order simulator.
- `backtest.py` MUST NOT add next-open, MOC, intraday, broker, or multi-asset execution semantics in this change.
- `backtest.py` MUST NOT support shorting or leverage in this change.
- `strategy/*` MUST NOT redefine the execution law.
- `metrics.py`, `report.py`, `storage.py`, and `cli.py` MUST NOT reinterpret the execution metadata as a different execution model.

#### Inputs / outputs / contracts

- Inputs:
  - loader-accepted OHLCV market data
  - strategy target positions
  - `BacktestConfig`
- Outputs:
  - an equity curve based on the legacy close-to-close lagged execution law
  - a trade log derived from executed position transitions
  - explicit execution metadata carrying the fields listed above

#### Invariants

- Position bounds remain `[0.0, 1.0]`.
- Shorting remains unsupported.
- Leverage remains unsupported.
- Execution remains close-to-close and one-bar lagged.
- The emitted metadata must describe the canonical execution law rather than a hypothetical future simulator.

#### Cross-module dependencies

- `storage.py` may serialize the metadata into persisted artifacts.
- `report.py` may surface the metadata for display, but it must not change the semantics.
- `cli.py` may print the metadata, but it must not invent a second execution law.

#### Failure modes if this boundary is violated

- Downstream modules can start assuming a different execution timing rule than the backtest actually uses.
- Users can misread the runtime as supporting leverage, shorting, or intraday order simulation when it does not.
- Report and storage outputs can drift from the actual backtest execution law if the metadata stays implicit.

#### Migration notes from current implementation

- The current runtime already behaves like a close-to-close, one-bar-lagged, long-only execution model.
- The change makes that behavior explicit and machine-readable rather than inferred from implementation details.

#### Open questions / deferred decisions

- None for the current execution law.

#### Scenario: runtime execution metadata is explicit

- GIVEN a future experiment run or persisted artifact
- WHEN execution semantics are serialized
- THEN the metadata SHALL include `legacy_close_to_close_lagged`
- AND it SHALL include the exact position, return, bounds, shorting, and leverage fields listed above

### Requirement: trade logs are return-based and must not be labeled as dollar PnL

`src/alphaforge/backtest.py` SHALL own a return-based trade-log contract whose fields describe returns and holding periods, not dollar accounting.

#### Purpose

- Keep trade semantics aligned with the execution law and avoid implying shares-level or broker-like accounting.
- Make the trade log usable for research diagnostics without pretending it is a ledger.

#### Canonical owner

- `src/alphaforge/backtest.py` is the authoritative owner of trade extraction semantics.
- `src/alphaforge/metrics.py` is the authoritative owner of win-rate computation from the return-based trade data.
- `src/alphaforge/storage.py` is the authoritative owner of the persisted `trade_log.csv` schema.

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

#### Cross-module dependencies

- `metrics.py` consumes `trade_net_return` values to compute win rate.
- `storage.py` serializes the return-based trade log.
- `report.py` may present the trade log using user-facing wording, but it must preserve the return-based meaning.

#### Failure modes if this boundary is violated

- Trade logs become ambiguous about whether they represent returns or dollar accounting.
- Downstream metrics can silently compute win rate from the wrong field.
- Report labels and persisted artifacts can drift apart on the meaning of the same trade record.

#### Migration notes from current implementation

- The current canonical trade-log shape uses PnL-shaped labels.
- This change requires a controlled rename to return-based field names instead of preserving the old names as the canonical schema.
- Any legacy reader, if one is introduced, must be clearly marked as compatibility-only and must not become the new default contract.

#### Open questions / deferred decisions

- Whether a temporary compatibility reader is needed for historical artifacts is deferred.
  - Recommended default: prefer a single coordinated rename for the canonical schema and update downstream consumers in the same migration.

#### Scenario: trade log uses return terminology only

- GIVEN a future persisted trade log
- WHEN the schema is emitted or reviewed
- THEN the fields SHALL be the return-based fields listed above
- AND the canonical schema SHALL NOT use `net_pnl` or other dollar-PnL labels
