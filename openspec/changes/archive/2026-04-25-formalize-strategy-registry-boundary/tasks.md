# Tasks

## 1. Spec and contract alignment

- [x] 1.1 Create proposal, design, tasks, and spec delta for the strategy registry boundary.
- [x] 1.2 Validate the OpenSpec change before runtime implementation.

## 2. Code migration

- [x] 2.1 Add `src/alphaforge/strategy_registry.py` with explicit registrations for existing strategy families.
- [x] 2.2 Update search-space validation and candidate validation to consume registry metadata.
- [x] 2.3 Update runner/protocol and permutation strategy construction to use registry dispatch.
- [x] 2.4 Update train-window validation, comparison family validation, and CLI choices/defaults to derive from registry-backed helpers.

## 3. Verification

- [x] 3.1 Add focused tests for registry metadata, construction, unsupported errors, search-space behavior, train-window behavior, and stale ownership checks.
- [x] 3.2 Run targeted tests, OpenSpec validation, and full pytest.

## 4. Cleanup

- [x] 4.1 Confirm no stale independently-owned `SUPPORTED_STRATEGY_FAMILIES` source remains outside the registry.
- [x] 4.2 Mark tasks complete and log implementation steps through the local Obsidian workflow.
