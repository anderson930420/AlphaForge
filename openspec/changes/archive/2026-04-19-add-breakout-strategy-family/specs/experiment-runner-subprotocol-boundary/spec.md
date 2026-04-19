# Delta for Experiment Runner Subprotocol Boundary

## ADDED Requirements

### Requirement: shared runner helper dispatch resolves the supported strategy family set

`src/alphaforge/runner_protocols.py` SHALL keep shared runner helper logic orchestration-only while routing strategy specs to the current supported strategy implementations.

#### Supported strategy family set

- `ma_crossover`
- `breakout`

#### Canonical owner

- `src/alphaforge/runner_protocols.py` remains the authoritative owner of shared runner helper logic, including `build_strategy()` dispatch.
- `src/alphaforge/strategy/ma_crossover.py` and `src/alphaforge/strategy/breakout.py` remain the implementation owners for their respective strategy semantics.

#### Allowed responsibilities

- `runner_protocols.py` MAY instantiate either supported strategy implementation from a `StrategySpec`.
- `runner_protocols.py` MAY continue to own family-agnostic helper logic such as split generation and validation metadata assembly.

#### Explicit non-responsibilities

- `runner_protocols.py` MUST NOT own strategy formulas or strategy-family parameter semantics.
- `runner_protocols.py` MUST NOT encode a generic plugin registry.
- `runner_protocols.py` MUST NOT make breakout appear as a variation of MA crossover.

#### Inputs / outputs / contracts

- Inputs:
  - `StrategySpec.name`
  - `StrategySpec.parameters`
- Output:
  - a concrete strategy instance for the named supported family

#### Invariants

- Shared helper dispatch remains finite and explicit for the current family set.
- The helper module remains orchestration-only and does not absorb strategy semantics.

#### Scenario: build_strategy dispatches breakout explicitly

- GIVEN a `StrategySpec` with `name="breakout"`
- WHEN `runner_protocols.py` builds the strategy
- THEN it SHALL return the breakout strategy implementation
- AND it SHALL NOT return an MA crossover strategy
