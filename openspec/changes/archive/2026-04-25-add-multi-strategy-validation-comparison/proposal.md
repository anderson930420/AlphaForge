## Why

AlphaForge can validate one strategy family at a time, but research comparisons currently require manual, error-prone repetition across families. A reproducible research workflow needs to run supported strategy families against the same dataset, split, backtest settings, scoring function, permutation settings, and research policy decision flow.

## What Changes

- Add an MVP multi-strategy comparison workflow for `ma_crossover` and `breakout`.
- Reuse the existing `validate-search` workflow per strategy family.
- Select one best train candidate per family, evaluate it on the shared test split, optionally run permutation evidence, and apply the existing research policy.
- Persist comparison-level JSON and CSV artifacts plus per-family validation artifacts in separate directories.
- Add a CLI command, `alphaforge compare-strategies`, that assembles request/config objects and dispatches to the workflow layer.

## Impact

- Adds runtime schemas for comparison request/result contracts.
- Adds storage-owned comparison artifact serialization and layout.
- Adds workflow orchestration that loops over supported strategy families without duplicating validation, scoring, permutation, or policy logic.
- Adds CLI and test coverage for comparison execution, artifact persistence, permutation propagation, and unsupported strategy rejection.
