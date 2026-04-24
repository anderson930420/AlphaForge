# Tasks

## 1. OpenSpec

- [x] 1.1 Create proposal, design, tasks, and delta spec for the holdout cutoff boundary.
- [x] 1.2 Validate the OpenSpec change.

## 2. Implementation

- [x] 2.1 Add a holdout split helper in the data-loading boundary.
- [x] 2.2 Thread `holdout_cutoff_date` through the runner facade, workflows, and CLI where needed.
- [x] 2.3 Preserve existing behavior when no cutoff is configured.

## 3. Tests

- [x] 3.1 Add split-helper coverage for development and holdout partitioning.
- [x] 3.2 Add failure coverage for empty development, empty holdout, invalid cutoff, and missing datetime.
- [x] 3.3 Add workflow coverage showing development-only execution when a cutoff is provided.
- [x] 3.4 Add regression coverage showing unchanged behavior without a cutoff.

## 4. Verification

- [x] 4.1 Run `openspec validate add-holdout-cutoff-data-boundary --type change --no-interactive`.
- [x] 4.2 Run `pytest`.
- [x] 4.3 Log meaningful implementation and verification steps to Obsidian.
