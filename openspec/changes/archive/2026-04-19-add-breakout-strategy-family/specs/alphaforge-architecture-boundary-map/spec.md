# Delta for AlphaForge Architecture Boundary Map

## ADDED Requirements

### Requirement: the architecture map recognizes breakout as a supported strategy implementation family

AlphaForge SHALL classify the breakout strategy as a first-class supported implementation family alongside MA crossover, and downstream layers SHALL treat it as an explicit named family rather than an implicit MA variant.

#### Canonical ownership updates

- `src/alphaforge/strategy/ma_crossover.py` remains implementation-only for MA crossover.
- `src/alphaforge/strategy/breakout.py` becomes implementation-only for breakout.
- `src/alphaforge/search.py` remains implementation-authoritative for parameter-grid expansion and strategy-spec generation for supported strategy families.
- `src/alphaforge/runner_protocols.py` remains orchestration-only for shared strategy dispatch helpers.
- `src/alphaforge/cli.py` remains orchestration-only for family selection and request assembly.

#### Layer map updates

- Domain implementation layer:
  - `src/alphaforge/strategy/ma_crossover.py` is implementation-only for MA crossover strategy logic.
  - `src/alphaforge/strategy/breakout.py` is implementation-only for breakout strategy logic.
- Orchestration layer:
  - `src/alphaforge/runner_protocols.py` may route `StrategySpec.name` to the supported strategy implementations.
  - `src/alphaforge/experiment_runner.py` and `src/alphaforge/runner_workflows.py` continue to sequence workflows only.
- CLI layer:
  - `src/alphaforge/cli.py` may select between supported strategy families, but it may not define family semantics.

#### Cross-module dependency updates

- `search.py` depends on `strategy/ma_crossover.py` and `strategy/breakout.py` for family-specific semantic validation.
- `runner_protocols.py` depends on `strategy/ma_crossover.py` and `strategy/breakout.py` for supported strategy construction.
- `report.py`, `storage.py`, and `cli.py` remain downstream consumers of the chosen family and parameter mapping.

#### Failure modes if this boundary is violated

- If breakout is treated as an MA variant rather than a supported family, search validation and reporting will keep accreting MA-only assumptions.
- If strategy implementation ownership is not explicit, family-specific validation can be duplicated across search, runner, and strategy modules.
- If CLI family selection is not explicit, users will be forced to encode family choice through parameter-name hacks.

#### Scenario: the architecture map includes both supported families

- GIVEN the AlphaForge architecture boundary map is read after this change
- WHEN a maintainer looks for supported strategy implementations
- THEN the map SHALL list both `ma_crossover` and `breakout`
- AND it SHALL keep their ownership separate from search, runner, CLI, storage, and report layers
