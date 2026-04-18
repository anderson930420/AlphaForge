# Design: configurable-permutation-target-metrics

## Canonical ownership mapping

- `src/alphaforge/permutation.py`
  - own target-metric validation,
  - own observed-versus-null comparison,
  - own target-metric value extraction for both the real run and each permutation.
- `src/alphaforge.schemas.py`
  - own the in-memory summary field names for metric value comparisons and count fields.
- `src/alphaforge.storage.py`
  - own persisted JSON serialization,
  - normalize count-like fields to integers before writing JSON,
  - keep filenames and artifact layout unchanged.
- `src/alphaforge.cli.py`
  - own parsing of `--target-metric`,
  - pass the selected metric name into the diagnostic runner,
  - fail syntactically on unsupported choices.

## Contract migration plan

- Replace the diagnostic’s hard-coded `score` comparison with a small supported metric vocabulary.
- Keep the null model, block permutation, seed handling, candidate immutability, and artifact filenames unchanged.
- Generalize the summary payload to metric-value terminology so the same contract works for both `score` and `sharpe_ratio`.
- Continue exposing the diagnostic as a storage-backed summary plus a score-list artifact, but treat the score-list field as the selected metric’s values.

## Duplicate logic removal plan

- Remove the implicit `score`-only boundary from `permutation.py`.
- Remove any serializer assumptions that count-like permutation summary fields can be emitted without explicit integer normalization.
- Remove test assumptions that the selected target metric is always `score`.

## Verification plan

- Add tests that run the diagnostic with `score` and `sharpe_ratio` and compare deterministic outputs.
- Add tests that invalid target metrics are rejected.
- Add tests that persisted JSON preserves integer typing for `permutation_count`, `seed`, `block_size`, and `null_ge_count`.
- Add CLI tests that verify the new option is wired through to the diagnostic and serialized summary.

## Temporary migration states

- During implementation, the diagnostic may briefly support both old and new field names if that helps preserve compatibility.
- If temporary duplication is used, the removal trigger is full test coverage for the new generic metric-value fields and updated canonical docs.
