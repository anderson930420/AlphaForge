# Proposal: stabilize-permutation-null-construction

## Boundary problem

- The permutation diagnostic currently creates null samples by shuffling absolute OHLCV rows in contiguous blocks.
- Moving-average and breakout strategies operate on absolute price paths, so stitching absolute blocks from unrelated price regimes can create artificial jumps at block boundaries.
- Rolling indicators can then span incompatible regimes, making the null distribution partially measure stitching artifacts instead of candidate edge.

## Canonical ownership decision

- `src/alphaforge/permutation.py` remains the canonical owner of null construction semantics.
- The canonical default null model becomes `return_block_reconstruction`.
- `src/alphaforge/schemas.py` owns the runtime summary field that records the null model.
- `src/alphaforge/storage.py` owns persistence of that null-model metadata.
- `src/alphaforge/cli.py` may surface the summary through existing serialization, but it must not define null construction logic.
- `metrics.py`, `backtest.py`, and `evidence.py` remain out of scope and must not be modified for this change.

## Scope

- Affected runtime flow: `permutation-test`.
- Affected null construction:
  - keep the first market-data row as the price anchor
  - convert later bars into OHLC values relative to the previous close
  - block-permute relative rows
  - reconstruct a continuous synthetic price path from the original anchor close
  - permute volume with the same relative block rows
- Affected summary metadata:
  - add `null_model: "return_block_reconstruction"`
  - preserve `permutation_mode`, `block_size`, `permutation_count`, and `seed`
- Explicitly out of scope:
  - full-search-procedure permutation
  - candidate promotion rules
  - validation policy changes
  - holdout cutoff
  - max reruns
  - GA
  - strategy registry
  - report redesign

## Migration risk

- CLI flags remain backward compatible; `--block-size`, `--seed`, `--target-metric`, and candidate arguments keep their current meanings.
- The null distribution values will change because the diagnostic now permutes relative returns and reconstructs prices instead of shuffling absolute OHLCV rows.
- Persisted JSON gains one metadata field while retaining existing fields.
- Historical permutation artifacts without `null_model` should be treated as using the previous block row shuffle semantics.

## Acceptance conditions

- OpenSpec validates for `stabilize-permutation-null-construction`.
- The permutation summary records `null_model == "return_block_reconstruction"`.
- Reconstructed synthetic market data preserves row count, canonical OHLCV columns, finite positive OHLC values, and datetime ordering shape.
- Same seed produces identical permutation metric values and p-value.
- Full pytest passes.
