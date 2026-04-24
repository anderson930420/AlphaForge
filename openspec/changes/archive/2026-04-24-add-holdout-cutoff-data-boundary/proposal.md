# Proposal: add-holdout-cutoff-data-boundary

## Boundary problem

- AlphaForge already supports validation, walk-forward, search, and permutation workflows against a canonical OHLCV dataset.
- Without an explicit final holdout boundary, those workflows can accidentally consume rows that should remain reserved for the final research freeze.
- That creates leakage risk that is distinct from ordinary train/test validation because the holdout region is meant to stay untouched until an explicit holdout-evaluation path is introduced.

## Canonical ownership decision

- `src/alphaforge/data_loader.py` is the canonical owner of the mechanical holdout split.
- Workflow orchestration in `runner_workflows.py` and the public facade in `experiment_runner.py` may request development-only data when a holdout cutoff is configured.
- `cli.py` may expose an optional user-facing cutoff flag, but it must not implement slicing rules itself.
- `metrics.py`, `backtest.py`, `permutation.py`, and `research_policy.py` remain unchanged as metric, execution, null-model, and policy owners respectively.
- `storage.py` may carry small metadata fields if the current artifact shape already supports them, but it must not become a holdout database.

## Scope

- Affected public concept: `holdout_cutoff_date`.
- Canonical meaning: the first datetime in the final holdout region.
- Development data: rows with `datetime < holdout_cutoff_date`.
- Holdout data: rows with `datetime >= holdout_cutoff_date`.
- Normal research workflows should use development-only rows by default when a holdout cutoff is configured.
- Explicitly out of scope:
  - GA
  - paper parsing / MCP
  - full one-time holdout reveal database
  - live trading
  - strategy registry
  - metric formula changes
  - research_policy runner integration beyond minimal boundary checks

## Migration risk

- Existing workflows without `holdout_cutoff_date` should remain unchanged.
- Workflows that opt in to the cutoff will fail fast if the split would erase either the development or holdout partition.
- Artifact metadata can record the holdout boundary without changing existing schema layouts.
- Any current tests that assume the full dataset is always available will need explicit holdout-free expectations when a cutoff is supplied.

## Acceptance conditions

- OpenSpec validates for `add-holdout-cutoff-data-boundary`.
- A helper exists that splits canonical market data into development and holdout partitions by datetime cutoff.
- The helper preserves row order and canonical OHLCV columns.
- The helper raises `ValueError` for missing datetime, invalid cutoff parsing, empty development partition, or empty holdout partition.
- Search, validate-search, walk-forward, and permutation-test workflows operate on development-only rows when a cutoff is provided.
- Holdout metadata is surfaced in workflow output where the current artifact structure already supports metadata dictionaries.
