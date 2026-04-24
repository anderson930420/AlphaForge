# Tasks

## 1. OpenSpec

- [x] 1.1 Create proposal, design, tasks, and candidate-evidence spec delta.
- [x] 1.2 Validate the OpenSpec change.

## 2. Implementation

- [x] 2.1 Inspect evidence, runner, metrics, schemas, and validation-related tests.
- [x] 2.2 Change `return_degradation` to use annualized returns from `MetricReport`.
- [x] 2.3 Keep public field names and schema shapes stable.

## 3. Tests

- [x] 3.1 Add a regression where test raw total return is lower but annualized return is equal or better.
- [x] 3.2 Add a direct test confirming `return_degradation` uses annualized returns, not total returns.
- [x] 3.3 Preserve existing validate-search behavior except for corrected degradation semantics.

## 4. Verification

- [x] 4.1 Run `openspec validate normalize-validation-return-degradation --type change --no-interactive`.
- [x] 4.2 Run `pytest`.
- [x] 4.3 Log meaningful implementation and verification steps to Obsidian.
