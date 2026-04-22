# execution-semantics-contract Specification

## Purpose
TBD - created by archiving change formalize-execution-semantics-contract. Update Purpose after archive.
## Requirements
### Requirement: `backtest.py` is the canonical owner of execution semantics

`src/alphaforge/backtest.py` SHALL be the single authoritative owner of execution semantics, including strategy-output interpretation, timing lag, turnover derivation, fee and slippage application, trade boundary detection, and equity-curve construction.

#### Purpose

- Freeze the execution law in one module so the meaning of a strategy output does not drift between strategy code, the backtest executor, metrics, reporting, storage, or orchestration.
- Make `backtest.py` the source of truth for what executed position, turnover, trade count, cost, and equity mean.

#### Canonical owner

- `src/alphaforge/backtest.py` is the only authoritative owner of execution semantics.
- `src/alphaforge/strategy/base.py` remains the interface owner for `generate_signals()` shape only.
- `src/alphaforge/strategy/ma_crossover.py` remains the signal-generation implementation for MA crossover.
- `src/alphaforge/strategy/breakout.py` remains the signal-generation implementation for breakout.
- `src/alphaforge/experiment_runner.py` remains orchestration-only.
- `src/alphaforge/metrics.py`, `src/alphaforge/report.py`, `src/alphaforge/visualization.py`, `src/alphaforge/storage.py`, and `src/alphaforge/cli.py` are downstream consumers only.
- `src/alphaforge/schemas.py` may define containers, but it must not become the semantic owner of execution behavior.

#### Allowed responsibilities

- `backtest.py` MAY interpret strategy output as a target-position input to execution.
- `backtest.py` MAY own the normalization path that converts strategy output into the supported execution domain.
- `backtest.py` MAY lag execution by one bar, derive turnover from executed positions, apply fees and slippage, extract trades, and compound equity.
- `backtest.py` MAY return the canonical in-memory execution artifact as an equity curve frame plus a trade-log frame.

#### Explicit non-responsibilities

- `strategy/base.py` MUST NOT own execution timing, lag semantics, clipping or normalization semantics, cost semantics, turnover semantics, or trade extraction semantics.
- `strategy/ma_crossover.py` and `strategy/breakout.py` MUST NOT own any generic execution rule.
- `experiment_runner.py` MUST NOT define execution law locally, even when it sequences backtest execution.
- `metrics.py` MUST NOT redefine turnover, trade count, or equity semantics.
- `report.py`, `visualization.py`, `storage.py`, and `cli.py` MUST NOT recompute or reinterpret executed positions, trades, or costs.

#### Inputs / outputs / contracts

- Inputs:
  - loader-normalized market data
  - a `pd.Series` returned by `Strategy.generate_signals()`
  - `BacktestConfig`
- Outputs:
  - canonical equity curve frame
  - canonical trade-log frame
- Contract rules:
  - the strategy signal series is consumed by `backtest.py` as execution input, not as an order stream
  - downstream modules must consume the returned execution artifacts as authoritative

#### Invariants

- One module owns execution semantics.
- The runtime execution artifact must not be reconstructed independently by downstream consumers.
- Any module outside `backtest.py` may observe execution results, but it may not redefine how they are produced.

#### Cross-module dependencies

- `backtest.py` consumes:
  - validated market data from `data_loader.py`
  - target-position series from `strategy/base.py` and strategy implementations
  - `BacktestConfig` from `schemas.py`
- `metrics.py` consumes the executed equity curve and trade log as authoritative inputs.
- `report.py`, `visualization.py`, `storage.py`, `cli.py`, and `experiment_runner.py` consume the executed outputs but do not own the execution law.

#### Failure modes if this boundary is violated

- If strategy code also owns execution timing, the same signal can produce different returns depending on call path.
- If metrics or report code re-derive turnover or trades, runtime summaries will disagree with persisted or displayed outputs.
- If orchestration starts owning execution rules, the backtest contract will drift as soon as a new workflow is added.

#### Migration notes from current implementation

- The current code already centralizes most execution steps in `backtest.py`, but the contract is still implicit in implementation details.
- This requirement makes that ownership explicit and prevents downstream modules from becoming secondary execution owners.

#### Open questions / deferred decisions

- None for ownership: `backtest.py` is the canonical owner.

#### Scenario: workflow callers delegate execution semantics to backtest

- GIVEN `experiment_runner.py` or `cli.py` needs to run a strategy
- WHEN it sequences a backtest
- THEN it SHALL pass market data, target positions, and config into `backtest.py`
- AND it SHALL NOT redefine timing, turnover, cost, or trade logic locally

### Requirement: Strategy output is a target-position contract, not an order contract

`Strategy.generate_signals()` SHALL produce a canonical target-position series for the next tradable interval, and `backtest.py` SHALL normalize that series into the supported long-flat execution domain.

#### Purpose

- Make the meaning of strategy output explicit.
- Remove ambiguity about whether strategy output is a raw signal, an order instruction, a desired exposure weight, or an executed position.

#### Canonical owner

- `src/alphaforge/strategy/base.py` owns the interface shape of `generate_signals()` only.
- `src/alphaforge/backtest.py` owns the interpretation and normalization of that output into executable positions.
- `src/alphaforge/strategy/ma_crossover.py` owns MA-specific signal generation only.
- `src/alphaforge/strategy/breakout.py` owns breakout-specific signal generation only.

#### Allowed responsibilities

- `generate_signals()` MAY return a `pd.Series` aligned to the input market-data index.
- The series MAY contain numeric values or values coercible to numeric form by `backtest.py`.
- `backtest.py` MAY normalize raw strategy output by coercing to float, filling missing values with `0.0`, and clipping values into the supported long-flat domain.

#### Explicit non-responsibilities

- `generate_signals()` MUST NOT define fill policy, lag policy, or cost policy.
- `generate_signals()` MUST NOT be documented as an order stream, fill stream, or trade stream.
- `strategy/base.py` MUST NOT claim ownership of normalization, clipping, timing, or cost semantics just because it defines the interface type.

#### Inputs / outputs / contracts

- Input contract:
  - the series should be index-compatible with the supplied market data
  - the output is interpreted as target position for the next tradable interval
- Normalization contract:
  - missing values are filled to `0.0`
  - values below `0.0` normalize to `0.0`
  - values above `1.0` normalize to `1.0`
- Supported execution domain:
  - `0.0` means flat
  - values between `0.0` and `1.0` inclusive remain long-only target exposure states
- Unsupported values:
  - negative weights are forbidden for the current execution contract
  - leverage above `1.0` is forbidden for the current execution contract

#### Invariants

- Strategy output is a target-position series, not an order instruction stream.
- The supported execution domain is long-flat only.
- The backtest owner is the only place where normalization semantics may be applied.
- Same-bar execution is not implied by the strategy interface.

#### Cross-module dependencies

- `strategy/base.py` defines the return type contract.
- `strategy/ma_crossover.py` and `strategy/breakout.py` produce strategy-specific values that enter the execution contract.
- `backtest.py` consumes the series and applies canonical normalization.
- `experiment_runner.py` passes the series through without redefining its meaning.

#### Failure modes if this boundary is violated

- If strategy output is treated as an order instruction, same-bar or quantity-based assumptions can leak into execution.
- If downstream code assumes unsupported negative or leveraged weights are preserved, backtest results and reports will disagree.
- If the interface wording implies hidden timing semantics, future strategies will inherit the wrong contract.

#### Migration notes from current implementation

- The current strategy interface docstring says "target position weights," which can be misread as either exposure sizing or order intent.
- The current MA crossover strategy already emits long-flat values, which matches the intended current domain.
- The current backtest implementation should be understood as the place where normalization semantics live, not the strategy interface.

#### Open questions / deferred decisions

- Whether upstream validation should fail fast on out-of-domain values before execution or whether `backtest.py` should remain the only normalization authority.
  - Recommended default: keep `backtest.py` as the normalization authority and add fail-fast validation only where it does not create a second semantic owner.
- Whether future short exposure should be admitted in the same execution mode or require a separate execution spec.
  - Recommended default: require a separate spec revision before short exposure is supported.

#### Scenario: a strategy emits NaNs and fractional values

- GIVEN a strategy returns a series containing NaNs and positive fractional values
- WHEN `backtest.py` normalizes the series
- THEN NaNs SHALL become flat exposure
- AND positive fractional values up to `1.0` SHALL be preserved as long-only target exposure
- AND the resulting execution state SHALL remain long-flat only

#### Scenario: same-bar execution remains forbidden

- GIVEN a strategy produces a target position on bar `t`
- WHEN the backtest runs
- THEN that target SHALL become active on bar `t+1`
- AND the first bar SHALL remain flat

### Requirement: Trade extraction, costs, and equity are derived from executed position transitions

`backtest.py` SHALL derive trade boundaries, turnover, fee and slippage costs, and equity curve values from executed position transitions only.

#### Purpose

- Make the execution-to-metrics pipeline explicit so later modules do not invent alternate turnover or trade logic.
- Ensure trade count, turnover, costs, and equity remain internally consistent because they are all derived from the same executed positions.

#### Canonical owner

- `src/alphaforge/backtest.py` is the canonical owner of position lag, turnover derivation, fee/slippage application, trade extraction, and equity construction.
- `src/alphaforge/metrics.py` is a consumer of those executed outputs only.
- `src/alphaforge/report.py`, `src/alphaforge/visualization.py`, `src/alphaforge/storage.py`, `src/alphaforge/cli.py`, and `src/alphaforge/experiment_runner.py` are downstream consumers only.

#### Allowed responsibilities

- `backtest.py` MAY compute `position` as the one-bar-lagged version of normalized `target_position`.
- `backtest.py` MAY compute `close_return` from close-to-close market data.
- `backtest.py` MAY compute turnover as the absolute change in executed position.
- `backtest.py` MAY compute trading cost from turnover and the configured fee and slippage rates.
- `backtest.py` MAY compute `strategy_return` and compound `equity`.
- `backtest.py` MAY extract a trade log by scanning executed position transitions.
- `backtest.py` MAY force-close any open long trade on the final bar.

#### Explicit non-responsibilities

- `metrics.py` MUST NOT redefine turnover, trade count, or cost formulas.
- `report.py` MUST NOT recompute execution outputs as part of presentation.
- `storage.py` MUST NOT define trade or turnover semantics through CSV layout.
- `cli.py` and `experiment_runner.py` MUST NOT reconstruct trade boundaries or costs from raw signals.

#### Inputs / outputs / contracts

- Inputs:
  - normalized target positions from the backtest owner
  - loader-normalized market data
  - `BacktestConfig.initial_capital`
  - `BacktestConfig.fee_rate`
  - `BacktestConfig.slippage_rate`
- Execution sequence:
  1. normalize strategy output
  2. lag execution by one bar
  3. compute close-to-close return
  4. derive turnover from executed position changes
  5. apply fee and slippage costs on turnover
  6. compute strategy return
  7. compound equity
- Output columns in the canonical in-memory execution artifact:
  - source market-data columns
  - `target_position`
  - `position`
  - `close_return`
  - `turnover`
  - `strategy_return`
  - `equity`
- Trade-log columns in the canonical runtime execution artifact:
  - `entry_time`
  - `exit_time`
  - `side`
  - `quantity`
  - `entry_price`
  - `exit_price`
  - `gross_return`
  - `net_pnl`

#### Invariants

- Turnover and trade count must come from the same executed position transition logic.
- Fees and slippage are applied only when position changes.
- Same-bar fills are forbidden.
- The first bar has no prior executed position, so it begins flat.
- The trade log is a derived runtime artifact, not a second semantic owner.

#### Cross-module dependencies

- `metrics.py` consumes the backtest outputs and must trust their turnover and trade count semantics.
- `report.py` and `visualization.py` consume the backtest outputs for display only.
- `storage.py` serializes the outputs but does not define them.
- `experiment_runner.py` and `cli.py` pass the outputs through workflow layers without redefining them.

#### Failure modes if this boundary is violated

- If turnover is computed from a different rule than trade extraction, trade count and cost totals will disagree.
- If costs are applied outside `backtest.py`, metric totals and report summaries will drift.
- If equity is reconstructed downstream, the stored artifact can stop matching the runtime result.
- If the final open trade is not force-closed, trade logs and realized net PnL will be inconsistent.

#### Migration notes from current implementation

- The current backtest implementation already lags positions, computes turnover from position changes, applies fees and slippage on turnover, and extracts trades from executed positions.
- The current contract simply makes those rules explicit so they do not leak into downstream modules as implied behavior.

#### Open questions / deferred decisions

- None for the current execution law: turnover, trade extraction, and equity are derived from executed position transitions owned by `backtest.py`.

#### Scenario: position transitions drive turnover and trades

- GIVEN executed position changes from flat to long and later back to flat
- WHEN `backtest.py` derives runtime artifacts
- THEN turnover SHALL be computed from the absolute position delta
- AND the trade log SHALL record one open and one close for the transition pair
- AND metrics SHALL use the executed turnover and trade log without recomputing them

#### Scenario: an open trade at the end of the sample is closed by the backtest owner

- GIVEN the final executed position remains long
- WHEN the backtest reaches the last bar
- THEN the trade log SHALL force-close the open trade at the final close price
- AND equity SHALL reflect the full executed path through the final bar

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

