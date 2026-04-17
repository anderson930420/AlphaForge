# Delta for Search Space and Search Execution Boundary

## ADDED Requirements

### Requirement: MA crossover search-space construction has a canonical parameter and invalid-combo contract

The MA crossover search family in `src/alphaforge/search.py` SHALL expose one canonical search-space contract for parameter enumeration and invalid-combination filtering.

#### Canonical MA search parameters

- `short_window`
- `long_window`

#### Constraint rules

- both parameters MUST be present for MA-family candidate construction
- both parameters MUST be positive integers
- `short_window` MUST be smaller than `long_window`

#### Coarse-search semantics

- the MA-family coarse search SHALL be a deterministic Cartesian expansion over the provided parameter lists
- parameter enumeration order MUST follow the parameter-grid key order
- candidate value order for each parameter MUST follow the input list order
- invalid MA combinations MUST be filtered explicitly before candidate execution
- invalid filtering MUST be deterministic for the same input grid

#### Invalid-combo handling contract

- invalid MA combinations SHALL be excluded from the returned candidate list
- invalid combinations MUST NOT be silently repaired or mutated into valid combinations
- if every attempted combination is invalid, the search-space owner SHALL raise a clear error instead of returning an empty valid-candidate set
- search-space evaluation output SHOULD expose attempted, valid, and invalid counts so downstream workflows can report the filtering result without re-deriving it

#### Scenario: MA invalid combinations are filtered explicitly

- GIVEN an MA parameter grid containing combinations where `short_window >= long_window`
- WHEN the search-space owner evaluates that grid
- THEN those combinations SHALL be excluded from the valid candidate list
- AND the filtering SHALL be deterministic for repeated evaluations of the same grid

### Requirement: search ranking and top-N selection are deterministic and derived from canonical ranking output

`src/alphaforge/scoring.py` SHALL own deterministic ranking and top-N candidate-selection semantics for search results.

#### Ranking contract

- ranking MUST use the `ExperimentResult.score` field as the canonical comparison score
- threshold filtering MUST be applied before ranking
- ranking order MUST be deterministic for the same executed results and threshold inputs

#### Tie-break contract

- equal-score results MUST be ordered deterministically
- the deterministic tie-break order SHALL be:
  - strategy name ascending
  - strategy parameter key/value pairs in canonical sorted-key order ascending

#### Top-N contract

- top-N selection SHALL return the first `N` entries from the canonical ranked list, or all entries when fewer than `N` exist
- `best_result` SHALL be identical to rank 1 when the ranked list is non-empty
- `best_result` SHALL be `None` when the ranked list is empty
- `top_results[0]` SHALL equal `best_result` whenever `top_results` is non-empty

#### Scenario: equal-score results rank deterministically

- GIVEN two or more executed results with the same `score`
- WHEN the ranking owner orders them
- THEN the order SHALL be deterministic under the canonical tie-break contract
- AND repeated ranking calls SHALL produce the same result order

### Requirement: search workflow summaries have a stable contract derived from search, scoring, and artifact receipts

The search workflow SHALL expose a stable summary contract assembled by the runner from authoritative search-space facts, ranking outputs, and optional artifact receipts.

#### Required summary fields

- `strategy_name`
- `search_parameter_names`
- `attempted_combinations`
- `valid_combinations`
- `invalid_combinations`
- `result_count`
- `ranking_score`
- `best_result`
- `top_results`

#### Artifact-reference fields

- `ranked_results_path` when ranked results were persisted
- `report_path` when the best-result report was generated
- `search_report_path` when the comparison report was generated

#### Relation contract

- `result_count` SHALL equal the length of the canonical ranked result list
- `best_result` SHALL equal the first ranked result when `result_count > 0`
- `top_results` SHALL preserve ranked order and SHALL be a prefix of the canonical ranked result list
- when `ranked_results_path` exists, the persisted ranked-results artifact SHALL represent the same ranking order summarized by `best_result` and `top_results`

#### Scenario: search summary remains aligned with persisted ranking

- GIVEN a search workflow persists ranked results and returns a search summary
- WHEN a user inspects `best_result`, `top_results`, and `ranked_results_path`
- THEN those surfaces SHALL describe the same canonical ranking order
- AND no downstream layer SHALL infer a conflicting candidate-selection rule
