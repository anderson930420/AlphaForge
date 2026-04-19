# Tasks

## 1. Spec and contract alignment

- [ ] 1.1 Update the OpenSpec proposal and boundary deltas so the supported family set, strategy dispatch, CLI request assembly, and presentation/storage contracts all name `breakout` explicitly.
- [ ] 1.2 Identify every downstream adapter or presentation helper that must derive from the selected strategy parameters instead of MA-only names.

## 2. Code migration

- [ ] 2.1 Add `src/alphaforge/strategy/breakout.py` with narrow long/flat breakout signal generation and parameter validation.
- [ ] 2.2 Extend `search.py` so named family candidate generation works for both `ma_crossover` and `breakout`.
- [ ] 2.3 Update `runner_protocols.py`, `runner_workflows.py`, and `experiment_runner.py` so search-like workflows accept an explicit strategy family and dispatch it correctly.
- [ ] 2.4 Update `cli.py` so `run`, `search`, `validate-search`, and `walk-forward` can assemble breakout requests as well as MA crossover requests.
- [ ] 2.5 Update `search_reporting.py`, `report.py`, and `storage.py` so family-specific labels and fold-result columns are derived from `StrategySpec.parameters`.

## 3. Verification

- [ ] 3.1 Add or update tests for breakout signal generation, parameter validation, and family-specific search-space generation.
- [ ] 3.2 Add or update tests for runner dispatch, CLI request assembly, report labels, and storage output columns.
- [ ] 3.3 Re-run the MA regression tests to confirm current behavior remains stable.

## 4. Cleanup

- [ ] 4.1 Remove MA-only hardcoding that becomes redundant once breakout is wired through the shared family-aware path.
- [ ] 4.2 Update README examples only if the user-facing command surface changes enough to require a new breakout example.
- [ ] 4.3 Log each meaningful implementation step through the local Obsidian workflow before marking the change complete.
