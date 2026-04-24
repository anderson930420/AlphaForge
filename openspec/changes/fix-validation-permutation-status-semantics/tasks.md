# Tasks

## 1. OpenSpec

- [x] 1.1 Create proposal, design, tasks, and spec delta artifacts.
- [x] 1.2 Validate the OpenSpec change.

## 2. Implementation

- [x] 2.1 Replace validation permutation status values with skipped, completed_passed, completed_failed, and error.
- [x] 2.2 Separate execution errors from p-value threshold failures in the validation workflow.
- [x] 2.3 Keep research policy verdict behavior unchanged.

## 3. Tests

- [x] 3.1 Add tests for execution error, completed_failed, completed_passed, and skipped.
- [x] 3.2 Update storage and validation assertions to use the new status vocabulary.

## 4. Verification

- [x] 4.1 Run `openspec validate fix-validation-permutation-status-semantics --type change --no-interactive`.
- [x] 4.2 Run `pytest -q`.
- [x] 4.3 Log meaningful implementation and verification steps to Obsidian.
