# Tasks

## 1. OpenSpec

- [x] 1.1 Create proposal, design, tasks, and spec delta artifacts.
- [x] 1.2 Validate the OpenSpec change.

## 2. Implementation

- [x] 2.1 Add a validation permutation config and CLI flags.
- [x] 2.2 Add a shared permutation helper that can run against an already-selected validation candidate/test window.
- [x] 2.3 Thread permutation summary and status into validation evidence, research policy, and persisted validation artifacts.
- [x] 2.4 Keep validate-search default behavior unchanged when permutation testing is not requested.

## 3. Tests

- [x] 3.1 Add CLI tests for permutation flags and default behavior.
- [x] 3.2 Add workflow tests for candidate selection, strategy coverage, permutation summary propagation, and policy integration.
- [x] 3.3 Add storage tests for validation permutation artifacts and summary references.
- [x] 3.4 Add opt-out and unavailable-evidence tests.

## 4. Verification

- [x] 4.1 Run `openspec validate integrate-permutation-evidence-into-validation-workflow --type change --no-interactive`.
- [x] 4.2 Run `pytest -q`.
- [x] 4.3 Log meaningful implementation and verification steps to Obsidian.
