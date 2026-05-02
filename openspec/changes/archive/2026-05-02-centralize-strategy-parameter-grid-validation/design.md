# Design: centralize-strategy-parameter-grid-validation

## Canonical ownership mapping

- `src/alphaforge/strategy_registry.py` owns expected parameter names and parameter-grid key validation.
- `src/alphaforge/search.py` owns Cartesian product generation and candidate-combination filtering, but delegates parameter-grid key validation to the registry.
- `src/alphaforge/runner_workflows.py` owns workflow sequencing and can call registry validation before strategy comparison performs expensive work.
- `src/alphaforge/schemas.py` remains passive and does not import the registry.

## Contract migration plan

- Add `validate_parameter_grid_for_strategy(strategy_name: str, parameter_grid: ParameterGrid) -> None` to `strategy_registry.py`.
- The validator will:
  - call `get_strategy_registration(strategy_name)`,
  - compare `set(parameter_grid)` to `registration.parameter_names`,
  - raise `ValueError` for missing parameter names,
  - raise `ValueError` for unexpected parameter names,
  - include the strategy name and offending parameter names in errors.
- Replace `search.py`'s private `_validate_search_parameter_grid(...)` call with the registry validator.
- Update strategy comparison family validation to call the registry validator for each `StrategyFamilySearchConfig`.

## Duplicate logic removal plan

- Delete `_validate_search_parameter_grid(...)` from `search.py`.
- Remove missing/unexpected parameter-key comparison logic from `search.py`.
- Keep strategy-name lookup and unsupported-family errors in the registry.
- Keep dataclass schema construction passive; do not add schema `__post_init__` validation.

## Verification plan

- Add or update tests for:
  - valid `ma_crossover` grid accepted by registry validation,
  - valid `breakout` grid accepted by registry validation,
  - missing parameter keys rejected with strategy name and missing names,
  - unexpected parameter keys rejected with strategy name and unexpected names,
  - `evaluate_strategy_search_space(...)` delegates to registry validation,
  - strategy comparison rejects invalid family grids before expensive work,
  - `schemas.py` does not import `strategy_registry.py`,
  - `_validate_search_parameter_grid` no longer exists,
  - `search.py` contains no independent missing/unexpected key validation logic.
- Run OpenSpec validation and full pytest.

## Temporary migration states

- No temporary duplicate validation ownership is planned.
