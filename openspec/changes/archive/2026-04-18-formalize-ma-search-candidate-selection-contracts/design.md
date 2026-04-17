# Design: formalize-ma-search-candidate-selection-contracts

## Summary

This change keeps the existing MA crossover search workflow intact, but makes its contracts explicit and deterministic. The implementation stays intentionally small:

1. Introduce an explicit MA-family search-space contract in `search.py`
2. Introduce explicit deterministic ranking/top-N helpers in `scoring.py`
3. Introduce a runner-owned search summary object that the CLI can surface without local business logic
4. Add focused tests around the frozen contracts

## Design decisions

### 1. Keep MA-family search-space rules in `search.py`

`search.py` already owns search-space construction, so the new contract should stay there instead of moving into CLI or runner helpers.

The change adds an explicit search-space evaluation object that describes:

- canonical search parameter names
- attempted combination count
- valid candidate list
- invalid parameter combinations that were filtered out deterministically

This keeps invalid-combo handling observable and testable without turning the CLI into a second search owner.

### 2. Preserve strategy-owned semantic validation

`MovingAverageCrossoverStrategy` remains the final semantic guard for MA parameters.

The search-space layer may pre-filter impossible MA combinations, but the strategy constructor still enforces:

- positive integer window lengths
- `short_window < long_window`

That preserves the existing search/strategy responsibility boundary.

### 3. Make ranking deterministic in `scoring.py`

The current ranking rule is effectively:

- threshold-filter executed results
- sort by `score` descending

This change keeps `score` as the canonical ranking field, but adds an explicit deterministic tie-break key so equal-score candidates do not depend on input order.

The tie-break order will be:

1. higher `score`
2. strategy name ascending
3. strategy parameter key/value pairs in canonical sorted-key order

That keeps the rule small, general, and deterministic without introducing speculative multi-objective abstractions.

### 4. Make top-N semantics explicit

Top-N selection is derived from the canonical ranked list and belongs with ranking semantics rather than CLI slicing.

The new rule is:

- `top_results(limit=N)` returns the first `min(N, result_count)` entries of the ranked list
- `best_result` is `top_results(limit=1)[0]` when results exist
- `best_result` must equal `top_results[0]` whenever `top_results` is non-empty

### 5. Assemble the search summary in the runner

The search workflow summary is a workflow output, so `experiment_runner.py` should assemble it from:

- search-space facts from `search.py`
- ranking facts from `scoring.py`
- optional artifact refs from storage/reporting receipts

This prevents the CLI from recomputing candidate-selection semantics and keeps report/presentation layers downstream-only.

## Planned code touch points

- `src/alphaforge/search.py`
- `src/alphaforge/scoring.py`
- `src/alphaforge/experiment_runner.py`
- `src/alphaforge/cli.py`
- `src/alphaforge/schemas.py`
- `src/alphaforge/storage.py` only if a serializer/helper is needed for the stable summary payload
- focused tests in `tests/test_search_scoring.py`, `tests/test_runner.py`, and `tests/test_cli.py`

## Risks and mitigations

- Risk: changing CLI payload keys could break downstream parsing.
  - Mitigation: preserve existing keys and add only the missing explicit contract fields needed for determinism and clarity.
- Risk: tie-breaking could unintentionally change existing equal-score order.
  - Mitigation: keep the rule simple, document it explicitly, and test it directly.
- Risk: adding a new summary object could blur runtime vs persistence ownership.
  - Mitigation: keep the summary as a runtime/workflow object; persisted artifact ownership remains in `storage.py`.
