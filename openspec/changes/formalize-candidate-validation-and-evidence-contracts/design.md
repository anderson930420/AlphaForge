# Design: formalize-candidate-validation-and-evidence-contracts

## Summary

This change keeps the current validation and walk-forward flows intact, but makes their evidence output explicit:

1. Introduce a candidate-evidence summary for post-search validation.
2. Introduce fold-level candidate-evidence summaries for walk-forward.
3. Introduce a walk-forward aggregate evidence summary derived from the fold summaries.
4. Serialize the new evidence objects through storage and expose them through the CLI without local inference.

## Design decisions

### 1. Candidate evidence is a runtime summary, not a workflow engine

The new summary objects will live in `schemas.py` because they are runtime contracts, not storage receipts.

The summary is intentionally small and explicit:

- strategy identity
- optional search ranking context
- train metrics
- test metrics
- benchmark-relative summary
- degradation summary
- artifact paths when they exist
- verdict/status

### 2. Degradation is a simple delta contract

The contract uses direct metric deltas rather than a broader research-scoring framework:

- `return_degradation = test.total_return - train.total_return`
- `sharpe_degradation = test.sharpe_ratio - train.sharpe_ratio`
- `max_drawdown_delta = test.max_drawdown - train.max_drawdown`

That stays aligned with the current metric model and avoids speculative policy layers.

### 3. Verdicts stay small

The evidence layer will use a tight vocabulary:

- `candidate`
- `validated`
- `rejected`
- `inconclusive`

Current validation and walk-forward flows should emit `validated` when evidence is complete.
`candidate` is reserved for search-only evidence.
`inconclusive` covers missing or partial evidence.
`rejected` is reserved for explicit future rejection policy and will be supported by the contract even if current flows do not emit it.

### 4. Walk-forward aggregate evidence is separate from per-fold candidate evidence

Walk-forward folds each have their own candidate-evidence summary because each fold can select a different candidate.

The aggregate walk-forward result gets its own summary with:

- fold counts
- aggregate test metrics
- aggregate benchmark metrics
- verdict/status
- artifact paths

This avoids falsely collapsing different fold-selected candidates into a single candidate identity.

### 5. Keep ownership boundaries clear

- `experiment_runner.py` assembles the summaries from authoritative lower-layer outputs.
- `storage.py` serializes them.
- `cli.py` displays them.
- `report.py` remains downstream of those decisions.

## Planned code touch points

- `src/alphaforge/schemas.py`
- `src/alphaforge/evidence.py`
- `src/alphaforge/experiment_runner.py`
- `src/alphaforge/storage.py`
- `src/alphaforge/cli.py`
- `src/alphaforge/walk_forward_aggregation.py` if a small helper is needed for aggregate evidence metrics
- tests in `tests/test_validation.py`, `tests/test_runner.py`, `tests/test_storage.py`, and `tests/test_cli.py`

## Risks and mitigations

- Risk: evidence summaries could become too large.
  - Mitigation: keep the summaries structured but compact, and avoid embedding raw workflow objects.
- Risk: walk-forward aggregate evidence could imply a single candidate when folds choose different candidates.
  - Mitigation: use a separate aggregate evidence summary and keep candidate evidence at the fold level.
- Risk: verdict semantics could drift into hidden policy.
  - Mitigation: keep verdict derivation explicit and test the helper directly.
