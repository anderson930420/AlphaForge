# Design: add-breakout-strategy-family

## Canonical ownership mapping

- `src/alphaforge/strategy/breakout.py`
  - own breakout-family parameter validation
  - own breakout long/flat signal generation
- `src/alphaforge/search.py`
  - own named family search-space expansion and candidate pruning
  - keep family-specific candidate ordering deterministic
- `src/alphaforge/runner_protocols.py`
  - own shared runner dispatch for supported strategy families
  - route `StrategySpec.name` to MA crossover or breakout
- `src/alphaforge/runner_workflows.py`
  - accept a strategy-family selector for search-like workflows
  - pass the family selector through to search-space generation and train-window validation
- `src/alphaforge/experiment_runner.py`
  - expose the public workflow entry points and keep them orchestration-only
- `src/alphaforge/cli.py`
  - parse `--strategy` for run/search/validate-search/walk-forward
  - assemble family-specific request DTOs
- `src/alphaforge/search_reporting.py`
  - build family-aware comparison labels from strategy parameters
- `src/alphaforge/report.py`
  - render family-agnostic search-comparison tables using the selected parameter keys
- `src/alphaforge/storage.py`
  - write walk-forward fold-result artifacts with parameter columns derived from the selected strategy spec
- tests under `tests/`
  - lock the family switch, breakout behavior, MA regressions, and output-shape changes

## Contract migration plan

- Add one new strategy module, `breakout.py`, with a narrow long/flat breakout rule and a single required parameter, `lookback_window`.
- Extend search-space generation so the search owner can construct either MA crossover or breakout candidates from an explicit `StrategySpec.name`.
- Thread a `strategy_name` selector through search-like runner workflows so validation and walk-forward can operate on breakout without inferring the family from parameter names.
- Extend CLI request assembly with an explicit `--strategy` selector and family-specific parameter arguments.
- Keep MA crossover as the default family so the current stable baseline does not change for existing commands.
- Keep the runtime, evidence, policy, and permutation layers unchanged except where they consume the family-aware requests and labels produced by the updated owners.

## Duplicate logic removal plan

- Remove MA-only hardcoding from search-space validation so breakout candidates are accepted and rejected through the same family-aware path.
- Remove MA-only strategy dispatch assumptions from runner protocol helpers.
- Remove MA-only request assembly assumptions from CLI search-like commands.
- Remove MA-only parameter labels from search comparison presentation helpers.
- Remove MA-only `fold_results.csv` parameter columns from storage and derive those columns from the selected strategy spec instead.
- Keep the permutation diagnostic on the current MA-only path; it is family-specific diagnostic code and does not need to become breakout-aware in this change.

## Verification plan

- Add unit tests for breakout signal generation and breakout parameter validation.
- Add search-space tests for breakout candidate construction, invalid-grid handling, and MA regression behavior.
- Add runner protocol tests for strategy dispatch and family-aware train-window validation.
- Add CLI tests that select breakout for run and search-like commands and verify the assembled request payloads.
- Add report/storage tests that confirm comparison labels and fold-result columns are derived from the selected strategy parameters rather than MA-only names.
- Re-run the existing MA workflow tests to confirm the default family behavior is unchanged.
- Validate the OpenSpec change after the tasks are complete and archive only when the implementation and contract tests pass.

## Temporary migration states

- During the migration, MA crossover remains the default family and the existing MA CLI flags stay available.
- If report or storage tests require a brief compatibility branch while the generic parameter labels are introduced, that branch should be removed once the breakout path and the MA regression tests both pass.
- No temporary registry or plugin layer is expected; the supported family set is intentionally small and explicit.
