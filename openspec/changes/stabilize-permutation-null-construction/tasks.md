# Tasks

## 1. OpenSpec

- [x] 1.1 Create proposal, design, tasks, and permutation-null spec delta.
- [x] 1.2 Validate the OpenSpec change.

## 2. Implementation

- [x] 2.1 Inspect permutation, CLI, storage, schemas, and permutation tests.
- [x] 2.2 Add canonical null-model metadata to runtime and persisted summaries.
- [x] 2.3 Replace absolute OHLCV block shuffling with return-block reconstruction.
- [x] 2.4 Preserve existing CLI flags, fixed-candidate behavior, target metrics, seed handling, and block-size semantics.

## 3. Tests

- [x] 3.1 Add regression coverage showing reconstructed paths avoid artificial absolute price-level jumps.
- [x] 3.2 Add coverage that summaries include `null_model == "return_block_reconstruction"` and block size.
- [x] 3.3 Add deterministic seed coverage for identical inputs and seed.
- [x] 3.4 Add reconstructed market-data integrity coverage for row count, canonical columns, finite values, and positive OHLC.
- [x] 3.5 Keep existing permutation CLI/storage behavior passing with minimal metadata updates.

## 4. Verification

- [x] 4.1 Run `openspec validate stabilize-permutation-null-construction --type change --no-interactive`.
- [x] 4.2 Run `pytest`.
- [x] 4.3 Log meaningful implementation and verification steps to Obsidian.
