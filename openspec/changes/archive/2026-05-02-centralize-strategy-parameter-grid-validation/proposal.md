# Proposal: centralize-strategy-parameter-grid-validation

## Boundary problem

- `strategy_registry.py` owns expected parameter-name metadata, but `search.py` still owns the validation logic that compares a parameter grid's provided keys against that metadata.
- `StrategyFamilySearchConfig` remains a passive dataclass, so invalid parameter grids can be represented until a workflow consumes them; this is acceptable, but workflow entrypoints should validate through the registry before expensive execution.
- Strategy comparison currently validates strategy-family names before execution, but it does not explicitly validate each family's parameter-grid keys at the same boundary.

## Canonical ownership decision

- `src/alphaforge/strategy_registry.py` becomes the canonical owner of parameter-grid key validation for registered strategy families.
- `src/alphaforge/search.py` stops owning missing/unexpected parameter-key validation and delegates to the registry-owned validator.
- `src/alphaforge/runner_workflows.py` may call the registry validator before strategy comparison execution.
- `src/alphaforge/schemas.py` remains passive and must not import `strategy_registry.py`.

## Scope

- Add a public registry validation helper for strategy parameter grids.
- Replace search-owned key validation with registry-owned validation.
- Validate every `StrategyFamilySearchConfig` in strategy comparison before expensive per-family validation/search/permutation execution begins.
- Add focused tests for registry validation, search delegation, comparison early rejection, and dependency-boundary guards.

## Migration risk

- CLI behavior risk is low because existing valid `ma_crossover` and `breakout` grids should continue to pass.
- Persisted artifact risk is low because this change does not alter artifact paths, JSON fields, CSV columns, or output schemas.
- Runtime behavior risk is concentrated in error messages for invalid parameter grids; errors should remain clear and include the strategy name plus offending parameter names.
- Dependency risk is controlled by keeping schemas passive and avoiding a schema-to-registry import.

## Acceptance conditions

- OpenSpec proposal, design, tasks, and spec delta exist and validate before implementation starts.
- `strategy_registry.py` exposes a public parameter-grid validation helper.
- `search.py` no longer defines `_validate_search_parameter_grid` or missing/unexpected parameter-key validation logic.
- Search and strategy comparison consume registry-owned validation.
- `schemas.py` does not import `strategy_registry.py`.
- Valid `ma_crossover` and `breakout` grids still pass.
- Invalid grids fail through registry-owned validation before expensive strategy comparison execution where practical.
- `openspec validate centralize-strategy-parameter-grid-validation --type change --no-interactive` and `pytest -q` pass.
