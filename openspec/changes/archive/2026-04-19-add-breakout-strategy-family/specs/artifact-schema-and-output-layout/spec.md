# Delta for Artifact Schema and Output Layout

## ADDED Requirements

### Requirement: walk-forward fold-result artifacts include the selected strategy parameters as dynamic columns

`src/alphaforge/storage.py` SHALL keep `fold_results.csv` as a storage-owned artifact while deriving its strategy-parameter columns from the selected strategy specs rather than hardcoding MA-only columns.

#### Purpose

- Keep persisted walk-forward outputs compatible with multiple supported strategy families.
- Prevent fold-result CSV layout from becoming a second MA-only contract.

#### Canonical owner

- `src/alphaforge/storage.py` remains the canonical owner of persisted artifact schema and output layout.
- `src/alphaforge/runner_workflows.py` remains the sequencing owner that provides fold results to storage.

#### Allowed responsibilities

- `storage.py` MAY write the selected strategy parameters into `fold_results.csv` as family-specific columns.
- `storage.py` MAY preserve deterministic parameter-column ordering from the selected strategy specification.
- `storage.py` MAY continue to include fold-level metrics, benchmark metrics, and fold path references in the walk-forward artifact.

#### Explicit non-responsibilities

- `storage.py` MUST NOT hardcode MA-only parameter columns into `fold_results.csv`.
- `storage.py` MUST NOT own strategy-family semantics or search-space semantics.

#### Inputs / outputs / contracts

- Inputs:
  - `WalkForwardResult`
  - fold-level `selected_strategy_spec`
  - fold-level metrics and benchmark summaries
- Output:
  - `fold_results.csv` with dynamic strategy-parameter columns appropriate for the selected family

#### Invariants

- The fold-results artifact remains storage-owned and deterministic.
- Parameter columns remain derived from the selected strategy spec rather than from a family-specific list embedded in storage code.

#### Scenario: breakout walk-forward folds persist breakout parameter columns

- GIVEN a walk-forward result whose selected strategy is breakout
- WHEN storage writes `fold_results.csv`
- THEN the CSV SHALL include the breakout parameter columns
- AND it SHALL NOT require MA crossover column names to be present
