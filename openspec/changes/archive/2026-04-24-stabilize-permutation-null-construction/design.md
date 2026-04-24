# Design: stabilize-permutation-null-construction

## Decision

Replace absolute OHLCV block shuffling with return-block reconstruction inside `src/alphaforge/permutation.py`.

The diagnostic will still evaluate one fixed candidate against a block-based null distribution, but each permuted frame will be created by:

1. keeping the first market-data row as an anchor,
2. converting rows after the first row into relative OHLC movement from the previous close,
3. block-shuffling relative rows,
4. reconstructing a continuous synthetic price path from the original starting close,
5. preserving row count, datetime sequence, and canonical OHLCV columns.

## Ownership

- `permutation.py` owns the null construction helper and null-model constant.
- `schemas.py` owns the runtime `PermutationTestSummary` field for `null_model`.
- `storage.py` owns serialization of `null_model`.
- `cli.py` continues to serialize the returned summary and does not define null construction.

## Implementation plan

1. Add `NULL_MODEL = "return_block_reconstruction"` in `permutation.py`.
2. Add `null_model` to `PermutationTestSummary`.
3. Update storage serialization to include `null_model`.
4. Replace the current absolute-row block shuffle helper with return-block reconstruction.
5. Keep `block_size`, `permutation_count`, `seed`, target metric behavior, CLI flags, and fixed-candidate evaluation intact.
6. Add tests for continuity, metadata, determinism, and reconstructed data integrity.

## Compatibility

- CLI flags remain unchanged.
- Existing JSON summary fields remain present.
- New JSON summaries include `null_model`.
- Historical summaries without `null_model` remain historical artifacts of the previous null construction.

## Out of scope

- full-search-procedure permutation
- candidate promotion rules
- validation policy changes
- holdout cutoff
- max reruns
- GA
- strategy registry
- report rendering changes
