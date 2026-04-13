# Proposal: formalize-search-space-and-search-execution-boundary

## Boundary problem

- `src/alphaforge/search.py` currently builds Cartesian parameter combinations and also filters out obviously invalid MA combinations, but the repo has not yet named the exact boundary between search-space generation, candidate validity, search execution, and ranking.
- `src/alphaforge/experiment_runner.py` currently orchestrates search, validation, and walk-forward flows, and it is easy for that orchestration layer to accumulate candidate-generation or ranking semantics if the boundary is not explicit.
- `src/alphaforge/scoring.py`, `src/alphaforge.strategy/*`, and `src/alphaforge.search_reporting.py` all touch search outputs in different ways, so best-candidate selection and downstream reuse need a precise ownership split.

## Canonical ownership decision

- `src/alphaforge/search.py` becomes the canonical owner of search-space generation and candidate construction semantics.
- `src/alphaforge/scoring.py` becomes the canonical owner of ranking, threshold filtering, and best-candidate selection semantics.
- `src/alphaforge/experiment_runner.py` remains the canonical owner of search execution orchestration, validation protocol orchestration, and walk-forward protocol orchestration as they reuse search outputs.
- `src/alphaforge.strategy/*` remain the canonical owners of strategy-specific semantic validity.

## Scope

- Parameter-grid expansion into ordered candidate `StrategySpec` objects.
- Candidate constructibility rules for the current search family.
- Execution of already-defined candidates through the runner workflow.
- Ranking and selection of the best candidate from executed results.
- Reuse of search outputs in validate-search and walk-forward orchestration.

## Migration risk

- If search-space generation remains implicit, `search.py`, strategy constructors, and runner helpers can continue to disagree about which candidate combinations are valid.
- If ranking semantics remain spread across runner and presentation layers, “best params” can drift depending on which workflow produced the result.
- If validation and walk-forward protocols keep redefining search behavior, plain search and train-slice search will diverge.

## Acceptance conditions

- `search.py` is the only owner of candidate enumeration semantics.
- `scoring.py` is the only owner of ranking and best-candidate selection semantics.
- `experiment_runner.py` only executes candidates and reuses authoritative search/ranking outputs.
- Validation and walk-forward workflows reuse the same candidate and ranking semantics rather than defining their own.
