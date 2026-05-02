# Tasks

## 1. Spec and contract alignment

- [x] 1.1 Create proposal, design, tasks, and spec delta for registry-owned parameter-grid validation.
- [x] 1.2 Validate the OpenSpec change before runtime implementation.

## 2. Code migration

- [x] 2.1 Add registry-owned parameter-grid validation helper.
- [x] 2.2 Remove search-owned `_validate_search_parameter_grid(...)` and delegate search validation to the registry helper.
- [x] 2.3 Validate every strategy comparison family grid through the registry before expensive execution.
- [x] 2.4 Preserve passive schemas and avoid schema-to-registry imports.

## 3. Verification

- [x] 3.1 Add focused tests for valid grids, missing keys, unexpected keys, search delegation, comparison early rejection, and passive schema/source guards.
- [x] 3.2 Run targeted tests, OpenSpec validation, and full pytest.

## 4. Cleanup

- [x] 4.1 Confirm no stale `_validate_search_parameter_grid` or search-owned missing/unexpected key validation remains.
- [x] 4.2 Mark tasks complete and log implementation steps through the local Obsidian workflow.
