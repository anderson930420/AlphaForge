# Design: formalize-permutation-null-comparison-layer

## Diagnostic shape

The first anti-overfitting check is intentionally narrow:

- input: a single MA `StrategySpec`, a market-data CSV, and a permutation count
- real run: evaluate the candidate on the original data
- null runs: evaluate the same fixed candidate on seed-controlled row permutations
- output: one compact summary artifact with the observed score, permutation scores, and an empirical p-value

## Ownership boundaries

- `permutation.py` computes the diagnostic and nothing else.
- `storage.py` writes the summary artifact and score-list artifact.
- `cli.py` only parses arguments, calls the diagnostic layer, and prints the returned payload.
- `policy.py` remains unchanged; permutation output is diagnostic evidence, not a candidate verdict.

## Determinism rules

- Permutations are row-wise shuffles of the loaded OHLCV frame.
- The candidate parameters stay fixed across all permutations.
- The permutation count is explicit and must be positive.
- The RNG seed is explicit so the same inputs produce the same null distribution.

## Output shape

The summary artifact should include:

- strategy name
- strategy parameters
- target metric name
- real observed score
- permutation scores
- permutation count
- seed
- empirical p-value
- artifact paths

The persisted score-list artifact should remain a simple, auditable tabular companion to the JSON summary.
