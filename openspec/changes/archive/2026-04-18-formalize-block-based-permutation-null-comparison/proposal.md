# Proposal: formalize-block-based-permutation-null-comparison

## Boundary problem

- AlphaForge already has a fixed-candidate permutation diagnostic, but the current null model shuffles whole OHLCV rows.
- Whole-row shuffling is deterministic and narrow, but it destroys too much local temporal structure for the MA crossover workflow.
- That makes the null too easy to beat for some normal MA candidates while still being too destructive to be a useful discriminator.

## Canonical ownership decision

- `src/alphaforge/permutation.py` remains the owner of the fixed-candidate null-comparison diagnostic.
- `src/alphaforge/schemas.py` remains the owner of the runtime summary contract.
- `src/alphaforge/storage.py` remains the owner of persisted filenames and summary layout.
- `src/alphaforge.cli.py` remains the owner of CLI parsing and output formatting.

## Scope

- Replace the current whole-row shuffle null with a block-based permutation null.
- Use contiguous non-overlapping blocks.
- Preserve row order within each block.
- Shuffle block order only.
- Add one explicit CLI/input parameter: `block_size`.
- Keep the diagnostic fixed-candidate, seed-controlled, and target-metric-based on `score`.
- Preserve the existing persisted artifact names unless a real contract mismatch requires a change.

## Out of scope

- Genetic algorithms
- Multiple null models in one pass
- Re-searching candidates per permutation
- White’s Reality Check, SPA, bootstrap families, or multiple-testing correction frameworks
- Heavy report or visualization additions

## Acceptance conditions

- The diagnostic preserves more local time structure than whole-row shuffling.
- The permutation summary records block-based semantics explicitly.
- Invalid block sizes fail clearly and deterministically.
- Tests lock down block semantics, summary fields, serialization types, and CLI/storage output consistency.
