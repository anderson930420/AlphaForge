# Design: formalize-search-space-and-search-execution-boundary

## Goal

- Freeze the separation between candidate generation, candidate validity, search execution, ranking, and downstream reuse so search-related workflows do not drift into overlapping ownership.

## Design summary

- Let `search.py` turn parameter grids into ordered `StrategySpec` candidates.
- Let strategy modules enforce their own semantic validity.
- Let `experiment_runner.py` execute candidates and reuse the same search and ranking semantics in validation and walk-forward.
- Let `scoring.py` remain the sole ranking owner.
- Let storage, reporting, and CLI consume the resulting business facts only.

## Assembly shape

- Search-space generation should remain reusable as a pure candidate factory.
- Search execution should remain a workflow over already-defined candidates.
- Ranking should remain a post-execution business rule with explicit thresholding and ordering.
- Validation and walk-forward should reuse the same search/ranking owners instead of defining alternate rules.

## Migration approach

- Preserve the current MA-search behavior while making the ownership split explicit.
- Keep the current runner orchestration paths, but ensure they call search and scoring rather than duplicating those rules.
- Avoid introducing any new search-specific logic into CLI, report, or storage code.

## Risks

- If search-family pruning moves into the runner, the boundary between search-space and orchestration will blur again.
- If ranking logic moves into report or CLI code, “best candidate” will no longer be a canonical business fact.
- If strategy constructors and search enumeration drift apart, callers will not be able to predict whether a candidate is valid until runtime.

