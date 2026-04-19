# Design: formalize-block-based-permutation-null-comparison

## Diagnostic shape

The diagnostic remains narrow:

- input: one MA `StrategySpec`, a market-data CSV, `permutation_count`, and `block_size`
- real run: evaluate the candidate on the original data
- null runs: evaluate the same fixed candidate on permuted data where the block order is shuffled
- output: observed score, null scores, null count, empirical p-value, and explicit block semantics

## Determinism rules

- Blocks are contiguous slices of the ordered OHLCV rows.
- Rows within each block keep their original order.
- The order of blocks is shuffled with the explicit seed.
- The block size must be positive and cannot exceed the number of rows.
- A trailing partial block is allowed and remains as its own block.

## Ownership boundaries

- `permutation.py` computes the diagnostic and the block permutation.
- `storage.py` writes the summary and score-list artifacts.
- `cli.py` only exposes the block size parameter and prints derived payloads.
- `policy.py` and the validation evidence layer remain unchanged.

## Output shape

The summary should preserve the existing fields and add:

- `permutation_mode = "block"`
- `block_size`

The artifact names should stay the same:

- `permutation_test_summary.json`
- `permutation_scores.csv`
