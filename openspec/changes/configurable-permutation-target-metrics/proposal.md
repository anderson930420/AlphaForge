# Proposal: configurable-permutation-target-metrics

## Boundary problem

- `src/alphaforge/permutation.py` currently hard-codes the comparison target to `score`, which prevents the permutation diagnostic from comparing another existing metric without changing the implementation.
- The persisted permutation summary currently forwards count-like fields through the serializer without explicit normalization, so a future string-typed input can leak into JSON as a string instead of an integer.

## Canonical ownership decision

- `src/alphaforge/permutation.py` becomes the authoritative owner of selecting the permutation target metric and comparing the observed value against permutation values.
- `src/alphaforge/storage.py` remains the authoritative owner of persisted permutation-summary serialization and must normalize integer count fields before writing JSON.
- `src/alphaforge/cli.py` remains a request-assembly and dispatch layer only; it may expose a target-metric flag, but it must not define the comparison semantics.

## Scope

- Permutation diagnostic request and summary contracts.
- Permutation CLI flag assembly for target-metric selection.
- Persisted permutation-summary JSON typing for count-like fields.
- Tests for score and sharpe-ratio target selection plus integer serialization.

## Migration risk

- CLI invocations that pass an unsupported target metric must now fail clearly instead of being accepted and silently compared against `score`.
- Persisted JSON shape will gain explicit metric naming for the observed and permuted comparison values, which may require downstream consumers to read the new generic field names.
- Existing diagnostic artifacts remain stable in filename and location, but their summary payload will become stricter about integer field typing.

## Acceptance conditions

- The permutation diagnostic can compare at least `score` and `sharpe_ratio`.
- The selected target metric name is recorded in the summary.
- The observed metric value and permutation metric values are serialized with stable field names.
- `null_ge_count`, `permutation_count`, `seed`, and `block_size` remain integers in persisted JSON.
- CLI and storage outputs stay aligned for the permutation diagnostic.
