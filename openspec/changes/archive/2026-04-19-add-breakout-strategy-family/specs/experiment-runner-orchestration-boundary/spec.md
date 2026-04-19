# Delta for Experiment Runner Orchestration Boundary

## ADDED Requirements

### Requirement: runner protocol dispatch supports the current explicit strategy family set

`src/alphaforge/runner_protocols.py` SHALL dispatch `StrategySpec.name` to the supported strategy implementations that AlphaForge currently exposes.

#### Supported strategy implementations

- `MovingAverageCrossoverStrategy`
- `BreakoutStrategy`

#### Canonical owner

- `src/alphaforge/runner_protocols.py` remains the canonical owner of shared runner-only helper logic, including strategy dispatch.
- `src/alphaforge/strategy/ma_crossover.py` remains the canonical owner of MA crossover implementation details.
- `src/alphaforge/strategy/breakout.py` becomes the canonical owner of breakout implementation details.

#### Allowed responsibilities

- `runner_protocols.py` MAY route a `StrategySpec` to the correct supported strategy implementation by name.
- `runner_protocols.py` MAY continue to own shared orchestration helpers such as default config assembly, train-window validation, split generation, and fold generation.

#### Explicit non-responsibilities

- `runner_protocols.py` MUST NOT own strategy signal formulas.
- `runner_protocols.py` MUST NOT own family-specific parameter semantics beyond dispatching to the correct strategy owner.
- `runner_protocols.py` MUST NOT become a strategy registry framework for hypothetical future families.

#### Inputs / outputs / contracts

- Inputs:
  - `StrategySpec.name`
  - `StrategySpec.parameters`
- Output:
  - a concrete supported strategy instance
- Contract rule:
  - unsupported strategy names MUST raise a clear error instead of falling through to MA-only behavior

#### Invariants

- Strategy dispatch remains explicit and finite for the current supported family set.
- Dispatch semantics remain orchestration-only and do not become a second source of strategy truth.

#### Scenario: breakout strategy dispatch is explicit

- GIVEN a `StrategySpec` with `name="breakout"`
- WHEN `runner_protocols.py` dispatches the strategy
- THEN it SHALL return the breakout strategy implementation
- AND it SHALL NOT route the spec through the MA crossover implementation
