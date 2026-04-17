# Proposal: formalize-ma-search-candidate-selection-contracts

## Boundary problem

- The current MA crossover search flow already works, but several important contracts are still implicit in code rather than explicitly frozen.
- `src/alphaforge/search.py` deterministically expands a grid and skips invalid MA combinations, but the canonical MA search parameters, invalid-combo policy, and coarse-search semantics are not documented as a stable contract.
- `src/alphaforge/scoring.py` ranks by `score` descending, but deterministic tie-breaking is not spelled out, so equal-score candidate order remains an implementation detail instead of an explicit rule.
- `src/alphaforge/cli.py` currently derives `best_result` and `top_results` by slicing the ranked list directly, which means top-N candidate-selection semantics live in presentation code instead of an upstream workflow contract.
- Search summaries expose useful fields today, but there is no explicit contract for the required summary keys, stable field names, or the relation between `best_result`, `top_results`, and the persisted ranked-results artifact.

## Canonical ownership decision

- `src/alphaforge/search.py` remains the owner of MA-family candidate enumeration, MA search-space rules, and deterministic invalid-combo filtering.
- `src/alphaforge/strategy/ma_crossover.py` remains the final semantic guard for MA parameter validity.
- `src/alphaforge/scoring.py` becomes the explicit owner of deterministic ranking, tie-breaking, and top-N candidate selection over executed results.
- `src/alphaforge/experiment_runner.py` becomes the owner of assembling the search workflow summary from authoritative search and scoring outputs.
- `src/alphaforge/cli.py` remains presentation-only for search summaries and must surface the upstream summary contract without re-deriving candidate-selection rules locally.

## Scope

- Formalize the canonical MA search parameters:
  - `short_window`
  - `long_window`
- Freeze the MA candidate-constraint rules:
  - both values must be positive integers
  - `short_window < long_window`
- Freeze deterministic invalid-combo filtering during MA search-space construction.
- Freeze coarse grid-search semantics for MA candidate generation.
- Freeze ranking semantics:
  - ranking uses `ExperimentResult.score`
  - threshold filtering is applied before ranking
  - tie-breaking is deterministic and explicit
- Freeze top-N semantics:
  - top results are the first `N` entries from the canonical ranked list
  - `best_result` is identical to rank 1 when results exist
- Freeze the stable search summary/output contract, including required fields and artifact-path relations.

## Out of scope

- Genetic algorithms
- Random search
- New strategy families
- Search-plugin architecture
- Broad experiment-runner redesign

## Acceptance conditions

- OpenSpec change artifacts explicitly describe the MA search/candidate-selection contract.
- Search-space construction exposes explicit MA-family constraints and deterministic invalid filtering.
- Ranking and top-N candidate selection are deterministic and owned upstream of the CLI.
- Search summaries expose a stable, documented contract with required fields and artifact refs.
- Tests lock valid/invalid combos, deterministic ranking, top-N selection, and summary/output stability.
- README only changes if the user-facing workflow contract changes materially.
