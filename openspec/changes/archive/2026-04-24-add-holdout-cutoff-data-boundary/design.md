# Design: add-holdout-cutoff-data-boundary

## Decision

`src/alphaforge/data_loader.py` will own a small helper that partitions canonical market data around a `holdout_cutoff_date`.

The helper will enforce:

```text
datetime column required
cutoff parseable as a timestamp/date
development rows: datetime < cutoff
holdout rows: datetime >= cutoff
```

It will fail fast when the split is meaningless:

- empty development partition
- empty holdout partition
- missing datetime column
- unparseable cutoff date

## Ownership

- `data_loader.py` owns the mechanical split because it already owns canonical market-data normalization.
- `runner_workflows.py` owns requesting development-only data for search, validation, walk-forward, and permutation workflows.
- `experiment_runner.py` remains a thin facade that forwards the optional cutoff.
- `cli.py` may accept a `--holdout-cutoff-date` flag and pass it through unchanged.
- `storage.py` may persist small metadata fields already supported by dict-backed metadata payloads.

## Implementation plan

1. Add a helper such as `split_holdout_data(market_data, holdout_cutoff_date)` in `data_loader.py`.
2. Thread an optional `holdout_cutoff_date` argument through the runner facade and workflow functions.
3. Apply the split before search, validation, walk-forward, and permutation workflow execution.
4. Preserve existing behavior when no holdout cutoff is configured.
5. Surface holdout metadata in workflow result metadata where dict-backed metadata already exists.
6. Add regression coverage for split semantics, failure modes, and one workflow using development-only rows.

## Compatibility

- Existing workflows without a cutoff remain unchanged.
- Strategies, metrics, execution formulas, and null-model construction are not modified.
- There is no holdout reveal database or holdout-specific runner path in this slice.

## Out of scope

- GA
- paper parsing / MCP
- full one-time holdout reveal database
- live trading
- strategy registry
- metric formula changes
- research_policy runner integration beyond minimal boundary checks
