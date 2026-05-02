# Delta for Research Policy and Metric Semantics

## ADDED Requirements

### Requirement: win rate is computed from positive trade net returns

`src/alphaforge/metrics.py` SHALL compute `win_rate` as the fraction of trades whose `trade_net_return` is greater than zero.

#### Purpose

- Keep win-rate semantics aligned with the return-based trade log.
- Prevent metric code from treating the trade log like a dollar PnL ledger.

#### Canonical owner

- `src/alphaforge/metrics.py` is the authoritative owner of the win-rate formula.
- `src/alphaforge/backtest.py` is the authoritative owner of the return-based trade-log fields that supply the input.
- `src/alphaforge/report.py` and `src/alphaforge/storage.py` are downstream consumers of the computed win rate only.

#### Allowed responsibilities

- `metrics.py` MAY compute `win_rate = count(trade_net_return > 0) / trade_count`.
- `metrics.py` MAY return `0.0` when `trade_count` is zero.
- `metrics.py` MAY ignore trades whose `trade_net_return` is zero or negative when counting wins.

#### Explicit non-responsibilities

- `metrics.py` MUST NOT compute win rate from dollar PnL labels.
- `metrics.py` MUST NOT rely on shares-level accounting or quantity-based profit reconstruction to determine win rate.
- `report.py` and `storage.py` MUST NOT redefine the win-rate formula locally.

#### Inputs / outputs / contracts

- Inputs:
  - the canonical return-based trade log
  - `trade_count`
- Output:
  - `win_rate`
- Contract rules:
  - the trade log field `trade_net_return` is the authoritative input for win counting
  - the win-rate rule is independent of any PnL-style legacy label that may exist in older artifacts

#### Invariants

- Positive return counts as a win.
- Zero or negative return does not count as a win.
- No-trade results return `0.0`.

#### Cross-module dependencies

- `backtest.py` provides the canonical return-based trade data.
- `report.py` may display the resulting metric, but it must not reinterpret it as a dollar accounting statistic.
- `storage.py` may serialize the metric, but it must not recalculate it from a different field.

#### Failure modes if this boundary is violated

- Different modules can disagree on what a "winning" trade is.
- A PnL-shaped legacy field can silently become the metric source of truth.
- Report summaries can diverge from metrics computations when they relabel the same trade contribution differently.

#### Migration notes from current implementation

- The current win-rate implementation already counts positive trade outcomes.
- This change makes the return-based input field and the formula explicit so the new trade-log schema and the metric formula stay aligned.

#### Open questions / deferred decisions

- None for the win-rate formula.

#### Scenario: return-based trade log yields the expected win rate

- GIVEN a trade log with three trades and `trade_net_return` values of `0.03`, `0.00`, and `-0.01`
- WHEN `metrics.py` computes win rate
- THEN the result SHALL be `1 / 3`
- AND the zero-return trade SHALL not count as a win
