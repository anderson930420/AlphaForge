# Delta for Permutation Null Comparison Contract

## ADDED Requirements

### Requirement: the permutation diagnostic supports every search-supported fixed candidate family it can construct explicitly

`src/alphaforge/permutation.py` SHALL build a fixed diagnostic candidate for both `ma_crossover` and `breakout`, returning the base `Strategy` type while keeping candidate parameters fixed across all permutations.

#### Purpose

- Let the diagnostic operate on the repo's supported fixed-candidate families without turning the permutation workflow into a search or registry system.
- Keep diagnostic strategy construction owned by `permutation.py` while the supported family list remains owned by `search.py`.

#### Canonical owner

- `src/alphaforge/permutation.py` remains the authoritative owner of permutation diagnostic strategy construction.
- `src/alphaforge/search.py` remains the authoritative owner of the supported strategy-family set.
- `src/alphaforge/strategy/base.py` remains the authoritative owner of the shared `Strategy` interface.

#### Allowed responsibilities

- `permutation.py` MAY construct either `MovingAverageCrossoverStrategy` or `BreakoutStrategy` from a fixed `StrategySpec`.
- `_build_strategy()` MAY return the shared `Strategy` base type.
- the diagnostic MAY reject only strategy families that are outside the supported family set or that it cannot construct explicitly.

#### Explicit non-responsibilities

- `permutation.py` MUST NOT generate candidates or rerun search per permutation.
- `permutation.py` MUST NOT define a concrete return type that falsely narrows the supported family set to MA crossover only.
- `cli.py` MUST NOT assemble a hardcoded MA-only `StrategySpec` for `permutation-test`.

#### Inputs / outputs / contracts

- Inputs:
  - `DataSpec`
  - fixed `StrategySpec`
  - permutation count, block size, target metric, seed, and backtest config
- Output:
  - a diagnostic summary for the fixed candidate
- Contract rules:
  - the fixed candidate parameters remain unchanged across permutations
  - supported target metrics remain `score` and `sharpe_ratio`
  - supported fixed candidate families include `ma_crossover` and `breakout`

#### Invariants

- One fixed candidate is evaluated on the real data and each permuted frame.
- Diagnostic family support stays aligned with the canonical search-supported family names.

#### Scenario: breakout uses the same fixed-candidate diagnostic contract

- GIVEN a breakout `StrategySpec`
- WHEN the permutation diagnostic runs
- THEN the diagnostic SHALL build one fixed breakout strategy instance per evaluation
- AND it SHALL compare the selected target metric against block-permuted null samples without rerunning search
