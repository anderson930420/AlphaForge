# Design: formalize-strategy-registry-boundary

## Canonical ownership mapping

- `src/alphaforge/strategy_registry.py` owns the registry record, registrations, supported-family list, registration lookup, and `StrategySpec` construction dispatch.
- `src/alphaforge/search.py` owns Cartesian grid expansion and search-space candidate generation, but reads expected parameter names and candidate validation behavior through registry metadata or registry-backed construction.
- `src/alphaforge/runner_protocols.py` owns runner protocol helpers, but delegates strategy construction and integer-window metadata lookup to the registry.
- `src/alphaforge/permutation.py` owns permutation diagnostic execution, but delegates fixed candidate construction to the registry.
- `src/alphaforge/cli.py` remains the request assembly boundary, but derives strategy choices and default comparison family names from the registry-backed supported family list.
- `src/alphaforge/strategy/ma_crossover.py` and `src/alphaforge/strategy/breakout.py` continue to own family-specific validation and signal-generation semantics.

## Contract migration plan

- Add `StrategyFamilyRegistration` with:
  - `name: str`
  - `parameter_names: tuple[str, ...]`
  - `integer_window_parameters: tuple[str, ...]`
  - `builder: Callable[[StrategySpec], Strategy]`
- Register exactly:
  - `ma_crossover` with `("short_window", "long_window")` and integer window parameter `("long_window",)`
  - `breakout` with `("lookback_window",)` and integer window parameter `("lookback_window",)`
- Expose:
  - `get_strategy_registration(strategy_name: str) -> StrategyFamilyRegistration`
  - `supported_strategy_families() -> tuple[str, ...]`
  - `build_strategy_from_registry(strategy_spec: StrategySpec) -> Strategy`
- Preserve current public compatibility where useful by allowing existing callers of `runner_protocols.build_strategy()` to receive registry-backed behavior.

## Duplicate logic removal plan

- Remove `SUPPORTED_STRATEGY_FAMILIES`, parameter-name tuples, and parameter-name mapping ownership from `search.py`; replace with registry-derived values.
- Remove direct concrete strategy imports and construction branches from `runner_protocols.py` and `permutation.py`.
- Remove the local required-history-parameter function from `runner_protocols.py`; train-window validation will use `integer_window_parameters`.
- Remove comparison family validation against search-owned constants in `runner_workflows.py`; use registry lookup or registry-backed supported-family helpers.
- Update CLI supported choices and default comparison strategies to derive from the registry.

## Verification plan

- Add registry-focused tests for:
  - exact current supported family names,
  - expected parameter names for `ma_crossover` and `breakout`,
  - clear unknown-strategy errors,
  - registry-backed construction type and behavior parity,
  - search-space evaluation for both existing families,
  - train-window validation using integer window metadata,
  - no stale independently-owned `SUPPORTED_STRATEGY_FAMILIES` source outside the registry.
- Run targeted tests for registry/search/runner protocol behavior before the full suite.
- Run `openspec validate formalize-strategy-registry-boundary --type change --no-interactive`.
- Run `pytest -q`.

## Temporary migration states

- No temporary duplicate ownership is planned.
- Existing `runner_protocols.build_strategy()` may remain as a compatibility wrapper, but its implementation must delegate to registry construction.
