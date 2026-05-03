# execution-semantics-contract Specification

## Purpose

Define the canonical execution semantics contract for AlphaForge backtests and make the current execution law explicit.

## MODIFIED Requirements

### Requirement: `backtest.py` emits explicit legacy close-to-close lagged execution semantics metadata

`src/alphaforge/backtest.py` SHALL be the canonical owner of the current execution semantics contract and SHALL emit explicit metadata describing the legacy execution law used by AlphaForge.

#### Scenario: runtime execution metadata is explicit

- GIVEN execution semantics are serialized
- WHEN AlphaForge reports the current execution law
- THEN it SHALL identify the execution model as `legacy_close_to_close_lagged`

## ADDED Requirements

### Requirement: `custom_signal` uses the existing legacy close-to-close lagged execution law

The `custom_signal` workflow SHALL use the same execution semantics as all other AlphaForge strategies and SHALL NOT introduce a second execution model.

#### Scenario: custom-signal target positions execute one bar later

- GIVEN a validated external `signal.csv` produces `target_position = float(signal_binary)`
- WHEN `backtest.py` executes the resulting target positions
- THEN `position[t] = target_position[t-1]`
- AND `close_return[t] = close[t] / close[t-1] - 1`
- AND `strategy_return[t] = position[t] * close_return[t] - transaction_cost[t]`
- AND the custom-signal workflow SHALL NOT claim next-open, MOC, intraday, shorting, leverage, or multi-asset execution semantics

### Requirement: scope remains execution-semantics only

This change SHALL NOT add a new simulator, a new order model, a new broker model, or any additional execution law.

#### Scenario: execution law remains unchanged for built-in strategies

- GIVEN AlphaForge runs `ma_crossover` or `breakout`
- WHEN the execution contract is observed
- THEN the existing legacy close-to-close lagged semantics SHALL remain unchanged
