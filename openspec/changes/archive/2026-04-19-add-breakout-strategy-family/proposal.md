# Proposal: add-breakout-strategy-family

## Boundary problem

- AlphaForge is still MA-only in the strategy-search and runner dispatch paths even though the runtime, evidence, policy, and orchestration boundaries are already stable.
- `search.py`, `runner_protocols.py`, and `cli.py` all still assume `ma_crossover` when constructing search candidates, building strategies, and assembling workflow requests for search-like flows.
- `search_reporting.py` and `report.py` still render search-comparison labels and parameter columns using MA-specific field names.
- That leaves the codebase unable to run a second family without either duplicating the MA path or introducing a broad registry abstraction too early.

## Canonical ownership decision

- `src/alphaforge/strategy/breakout.py` becomes the canonical owner of breakout-family signal generation and breakout-specific parameter validation.
- `src/alphaforge/search.py` remains the canonical owner of search-space enumeration and candidate construction, now for multiple explicit named strategy families.
- `src/alphaforge/runner_protocols.py` remains the canonical owner of runner-local strategy dispatch and will route `StrategySpec.name` to either MA crossover or breakout.
- `src/alphaforge/cli.py` remains the canonical owner of command parsing and request assembly, now including strategy-family selection for run/search/validate-search/walk-forward flows.
- `src/alphaforge/search_reporting.py` and `src/alphaforge/report.py` remain presentation owners and will derive user-facing labels from the selected strategy parameters instead of hardcoding MA-only labels.
- `src/alphaforge/storage.py` remains the persisted artifact owner and will continue to serialize strategy parameters generically rather than through MA-only column assumptions.

## Scope

- Strategy family implementation:
  - new `breakout` strategy module
  - long/flat breakout signal generation
  - breakout parameter validation
- Search-space support:
  - strategy-family selection in search candidate construction
  - breakout parameter-grid validation and candidate pruning
- Runner integration:
  - strategy dispatch for breakout in shared runner helpers
  - validate-search and walk-forward support for breakout search spaces
- CLI integration:
  - family selection for `run`, `search`, `validate-search`, and `walk-forward`
  - family-specific parameter assembly for MA crossover vs breakout
- Presentation and persistence cleanup:
  - generic search-comparison labels
  - generic walk-forward fold-result parameter columns
- Tests:
  - breakout strategy behavior
  - MA regression coverage
  - strategy dispatch
  - family-aware search validation
  - CLI request assembly for breakout
  - validation and walk-forward workflows for both families

## Migration risk

- CLI ergonomics will change because users must pick the strategy family when they want breakout instead of MA.
- Search comparison output and walk-forward fold-result artifacts will stop being MA-specific in their parameter labels and columns, so tests and docs must derive from the new generic labels.
- If search-space pruning and strategy-constructor validation diverge for breakout, the same candidate could be accepted in one path and rejected in another.
- If MA defaults are touched while breakout is added, the current stable baseline could regress even though the second family is the only intended addition.

## Acceptance conditions

- `breakout` can be selected from CLI and public runner entry points for `run`, `search`, `validate-search`, and `walk-forward`.
- `breakout` produces long/flat signals from a rolling breakout rule with a narrow parameter surface.
- Search ranking, validation, and walk-forward continue to reuse the same runtime, evidence, policy, persistence, and reporting owners.
- MA crossover behavior remains unchanged apart from the shared family-selection plumbing.
- Search and presentation artifacts show the correct family-specific parameter names without MA-only hardcoding.
