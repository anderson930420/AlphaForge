# search-space-and-search-execution-boundary Specification

## Purpose
Define the canonical named strategy-family search-space contract, including parameter enumeration, invalid-combination filtering, ranking handoff, and stable search-summary semantics.
## Requirements
### Requirement: `search.py` is the canonical owner of search-space generation and candidate construction

`src/alphaforge/search.py` SHALL be the single authoritative owner of AlphaForge search-space generation and candidate construction semantics for the supported strategy families.

#### Scenario: parameter grids become ordered StrategySpec candidates

- GIVEN a parameter grid for the MA crossover search family
- WHEN `search.py` expands the grid
- THEN it SHALL produce an ordered `list[StrategySpec]`
- AND that list SHALL be the canonical search-space contract consumed by the runner

#### Scenario: search-space generation does not execute strategies

- GIVEN a candidate `StrategySpec` list has been generated
- WHEN the search workflow continues
- THEN `search.py` SHALL NOT run backtests or compute scores
- AND execution SHALL be delegated to the orchestration owner

### Requirement: strategy modules own strategy-specific semantic validity; search owns enumeration only

`src/alphaforge/strategy/*` SHALL own strategy-specific semantic validity, while `src/alphaforge/search.py` SHALL own enumeration and candidate construction only.

#### Purpose

- Prevent a strategy implementation and the search owner from both acting as final validators for the same parameter rule.
- Keep semantic validity where the strategy implementation can enforce it at construction or signal-generation time.

#### Canonical owner

- `src/alphaforge/strategy/base.py` remains the owner of the strategy interface contract.
- `src/alphaforge/strategy/ma_crossover.py` remains the owner of MA crossover parameter validity and MA-specific strategy semantics.
- `src/alphaforge/strategy/breakout.py` remains the owner of breakout parameter validity and breakout-specific strategy semantics.
- `src/alphaforge/search.py` remains the owner of candidate enumeration and search-family-local pruning.

#### Allowed responsibilities

- Strategy modules MAY:
  - reject semantically invalid `StrategySpec` values for their own family,
  - enforce construction-time invariants such as positive window sizes or ordering constraints,
  - define candidate semantics that are unique to that strategy family.
- `search.py` MAY:
  - prefilter combinations that are impossible to instantiate for the target family,
  - use strategy-family-local pruning as a search optimization,
  - keep the candidate list deterministic and reusable.

#### Explicit non-responsibilities

- Strategy modules MUST NOT own generic Cartesian enumeration rules.
- `search.py` MUST NOT become the final semantic validator for strategy families.
- `search.py` MUST NOT encode execution, metric, or benchmark semantics under the guise of candidate validity.
- `search.py` MUST NOT invent hidden strategy-specific policy beyond the search-family constraints it explicitly owns.

#### Inputs / outputs / contracts

- Strategy-specific validity inputs:
  - `StrategySpec`
  - strategy-family parameters
  - strategy constructor or family-level invariants
- Search-space inputs:
  - strategy family name
  - parameter grid
- Contract rule:
  - search-space generation may avoid impossible candidates, but the strategy implementation remains the source of truth for whether a candidate is semantically valid for that strategy family

#### Invariants

- Candidate construction and semantic validity are related but not identical.
- Search-space pruning does not replace strategy validation.
- A candidate that survives search-space generation must still be accepted or rejected by the strategy owner according to its own rules.

#### Cross-module dependencies

- `experiment_runner.py` uses search-space output to dispatch strategy execution.
- `scoring.py` ranks executed candidates, not unexecuted parameter combinations.
- `cli.py` only assembles request DTOs for the search owner and the runner.

#### Failure modes if this boundary is violated

- Search starts duplicating strategy constructor checks, and the same invalid combination is rejected in two places for different reasons.
- Strategy implementations become hidden search engines by owning enumeration rules that should live in `search.py`.
- The same candidate can appear valid in one workflow and invalid in another because the source of truth is unclear.

#### Migration notes from current implementation

- `MovingAverageCrossoverStrategy` currently validates positive windows and `short_window < long_window` during construction.
- `build_strategy_specs()` currently also filters invalid MA combinations before construction.
- `BreakoutStrategy` currently validates a positive `lookback_window` during construction.
- `build_strategy_specs()` currently also filters invalid breakout combinations before construction.
- The current overlap is acceptable only if `search.py` is treated as the search-space prefilter and the strategy constructor is treated as the semantic guard.

#### Open questions / deferred decisions

- Whether the current MA-specific pruning should stay in `search.py` or be replaced by explicit strategy-family constraint descriptors is deferred.
  - Recommended default: keep the pruning in `search.py` for now and preserve the strategy constructor as the final semantic guard.

#### Scenario: strategy validity remains strategy-owned

- GIVEN a candidate `StrategySpec` reaches `MovingAverageCrossoverStrategy`
- WHEN the strategy is constructed
- THEN the strategy implementation SHALL enforce its own parameter invariants
- AND search-space generation SHALL NOT be treated as the final validator

### Requirement: `scoring.py` is the canonical owner of ranking and best-candidate selection semantics

`src/alphaforge/scoring.py` SHALL be the single authoritative owner of ranking, threshold filtering, and best-candidate selection semantics for AlphaForge search results.

#### Purpose

- Keep “best params” selection consistent across plain search, validation, and walk-forward reuse.
- Prevent runner, report, or CLI code from inventing alternative ranking rules.

#### Canonical owner

- `src/alphaforge/scoring.py` is the only authoritative owner of:
  - ranking filter rules,
  - score ordering,
  - best-candidate selection semantics derived from ranked results.
- `src/alphaforge/experiment_runner.py` must consume ranking outputs, not redefine them.
- `src/alphaforge/report.py` and `src/alphaforge/cli.py` may display ranked results, but they must not own the ranking truth.

#### Allowed responsibilities

- `scoring.py` MAY:
  - filter executed results by threshold criteria,
  - order results by score,
  - define which score field is used to compare candidates,
  - expose the first ranked candidate as the canonical best candidate for search-like workflows.

#### Explicit non-responsibilities

- `scoring.py` MUST NOT run backtests or generate candidates.
- `scoring.py` MUST NOT own search-space generation, execution orchestration, persistence layout, or report input semantics.
- `experiment_runner.py`, `report.py`, and `cli.py` MUST NOT redefine ordering, thresholding, or best-candidate semantics locally.

#### Inputs / outputs / contracts

- Inputs:
  - executed `ExperimentResult` objects
  - optional threshold caps such as maximum drawdown or minimum trade count
- Outputs:
  - ordered `list[ExperimentResult]`
  - the first element of that ordered list is the canonical best candidate when the list is non-empty
- Contract rule:
  - ranking is authoritative business output, not a presentation projection

#### Invariants

- The same executed results and the same threshold inputs must produce the same ranking order.
- Best-candidate selection is shared across plain search, validation, and walk-forward workflows when they reuse the same ranking rules.
- Presentation layers may display the ranking, but they may not reinterpret it.

#### Cross-module dependencies

- `experiment_runner.py` supplies executed results to `scoring.rank_results()`.
- `search_reporting.py`, `report.py`, and `cli.py` consume ranked outputs or best-result selections.
- `storage.py` may persist ranked outputs, but it does not define the business meaning of ranking.

#### Failure modes if this boundary is violated

- Different workflows choose different “best” candidates from the same executed results.
- Report and CLI output drift from the canonical best-candidate ordering because they apply their own sort or filter logic.
- Search and validation can no longer be compared because each path uses a different selection rule.

#### Migration notes from current implementation

- `score_metrics()` already computes the search score from metrics.
- `rank_results()` already filters by thresholds and sorts by score descending.
- `experiment_runner.py` already delegates to `rank_results()` for search, validation, and walk-forward selection.
- The current implementation is already aligned with this ownership split; the spec makes the split explicit so future refactors do not move ranking logic back into orchestration.

#### Open questions / deferred decisions

- Whether future multi-objective search will replace the single `score` field with a richer ranking contract is deferred.
  - Recommended default: keep `scoring.py` as the ranking owner and expand its contract explicitly if a second ranking mode is introduced.

#### Scenario: best candidate is the first ranked result

- GIVEN a non-empty set of executed results has been ranked
- WHEN the ranking owner returns the ordered list
- THEN the first result SHALL be the canonical best candidate
- AND no downstream module SHALL invent a different best-candidate rule

### Requirement: `experiment_runner.py` owns search execution and protocol reuse over already-defined candidates

`src/alphaforge/experiment_runner.py` SHALL be the canonical owner of search execution orchestration, validation protocol orchestration, and walk-forward protocol orchestration as they reuse search-space and ranking outputs.

#### Purpose

- Keep workflow sequencing in one place without letting the runner become the owner of candidate enumeration or ranking truth.
- Make the reuse relationship between plain search, validation, and walk-forward explicit.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` is the only authoritative owner of:
  - executing already-defined candidates through the workflow,
  - collecting candidate results,
  - invoking `scoring.rank_results()` to rank executed results,
  - reusing search outputs inside validation and walk-forward protocols,
  - selecting the best train candidate for validation and walk-forward test runs.
- `src/alphaforge/search.py` remains the authoritative owner of search-space generation.
- `src/alphaforge/scoring.py` remains the authoritative owner of ranking.
- `src/alphaforge/strategy/*` remain the authoritative owners of strategy semantics.

#### Allowed responsibilities

- `experiment_runner.py` MAY:
  - request candidate lists from `search.py`,
  - iterate candidates through strategy construction, backtest execution, metrics, benchmark summarization, and score ranking,
  - persist or report on search outputs by calling storage and report owners,
  - reuse ranked search outputs within validation and walk-forward protocols,
  - select the top-ranked candidate for downstream protocol execution.

#### Explicit non-responsibilities

- `experiment_runner.py` MUST NOT own search-space generation rules or candidate enumeration rules.
- `experiment_runner.py` MUST NOT own ranking semantics or best-candidate ordering.
- `experiment_runner.py` MUST NOT own execution semantics, metrics semantics, benchmark semantics, persistence layout, or report-view-model semantics.
- `experiment_runner.py` MUST NOT silently invent a different candidate list than the search-space owner returned.

#### Inputs / outputs / contracts

- Inputs:
  - ordered `list[StrategySpec]` from `search.py`
  - loader-accepted market data
  - workflow parameters for search, validation, and walk-forward protocols
- Outputs:
  - executed `ExperimentResult` collections
  - ranked executed results from `scoring.rank_results()`
  - validation and walk-forward results that reuse those ranked outputs
- Contract rules:
  - search execution must treat candidate semantics as read-only inputs
  - validation and walk-forward protocols may reuse search outputs, but they must not redefine search-space or ranking semantics

#### Invariants

- The runner may orchestrate different workflows, but it must not become the place where candidate enumeration or ranking truth lives.
- Search-like workflows always use the same ranking owner.
- Validation and walk-forward reuse the same search-space and ranking semantics while applying their own protocol-local slicing rules.

#### Cross-module dependencies

- `search.py` supplies the ordered candidate list.
- `strategy/base.py` and concrete strategy modules instantiate and validate strategies.
- `backtest.py`, `metrics.py`, and `benchmark.py` produce the per-candidate runtime facts.
- `scoring.py` ranks the executed results.
- `storage.py` persists derived artifacts.
- `report.py` renders derived report inputs.

#### Failure modes if this boundary is violated

- The runner begins to own candidate generation and search-space filtering, causing search behavior to diverge across callers.
- Plain search, validation, and walk-forward choose best candidates differently because the runner reimplements ranking locally.
- Search execution becomes hard to debug because orchestration and candidate semantics are mixed together.

#### Migration notes from current implementation

- `run_search_with_details()` already requests candidates from `search.py`, executes each candidate, and ranks the results through `scoring.rank_results()`.
- `run_validate_search()` and `run_walk_forward_search()` already reuse search outputs on train slices or folds before selecting the top-ranked candidate.
- `_validate_train_windows()` and fold generation remain runner-local protocol guards, which is appropriate as long as they do not redefine search-space semantics.
- The current implementation is already close to the desired split; this spec freezes it so future refactors do not pull candidate generation back into the runner.

#### Open questions / deferred decisions

- Whether runner-local protocol helpers should eventually move into a separate protocol module is deferred.
  - Recommended default: keep the orchestration owner in `experiment_runner.py` until a new protocol family makes extraction necessary.

#### Scenario: validation reuses search outputs instead of redefining search

- GIVEN a validation workflow splits data into train and test segments
- WHEN the train segment is searched
- THEN the runner SHALL reuse the search-space owner and the ranking owner
- AND it SHALL NOT redefine candidate enumeration or best-candidate selection locally

### Requirement: search outputs are downstream business facts for storage, reporting, and CLI consumption

Executed search outputs in AlphaForge SHALL be treated as downstream business facts for storage, reporting, and CLI consumption, not as separate owners of search truth.

#### Purpose

- Keep persisted search outputs and presentation surfaces derived from authoritative search, ranking, and orchestration owners.
- Prevent storage, reporting, or CLI code from becoming a parallel ranking or search-space authority.

#### Canonical owner

- `search.py`, `scoring.py`, and `experiment_runner.py` remain the canonical owners of their respective search boundaries.
- `storage.py` remains the canonical owner of persisted artifact naming and output layout.
- `report.py` remains the canonical owner of report-view-model semantics.
- `cli.py` remains the canonical owner of command output formatting only.

#### Allowed responsibilities

- `storage.py` MAY persist ranked search outputs and search summaries.
- `report.py` MAY render ranked search results and best-candidate summaries from explicit report inputs.
- `cli.py` MAY display ranked results, best-candidate summaries, and artifact refs returned by upstream owners.

#### Explicit non-responsibilities

- `storage.py` MUST NOT redefine ranking meaning when it writes ranked CSVs.
- `report.py` MUST NOT become the owner of best-candidate truth just because it renders search summaries.
- `cli.py` MUST NOT invent its own best-params semantics from printed summaries.
- None of these downstream layers MAY replace the ranking owner’s output with a locally computed alternative.

#### Inputs / outputs / contracts

- Inputs:
  - ranked `ExperimentResult` lists
  - optional artifact refs returned by storage
  - report-view-model inputs for search comparison views
- Outputs:
  - persisted ranked search artifacts
  - comparison reports
  - CLI summary payloads
- Contract rule:
  - downstream outputs are derived from authoritative search and ranking results, not parallel semantic owners

#### Invariants

- Search results remain comparable across workflows because the same ranking truth is reused everywhere.
- Persistence and presentation may change formatting or placement, but not the business meaning of search results.
- If a downstream surface shows a best candidate, it must come from the ranking owner’s ordered results.

#### Cross-module dependencies

- `storage.py` serializes ranked results and search summaries.
- `search_reporting.py` and `report.py` render search comparison artifacts.
- `cli.py` prints search summaries and artifact refs.

#### Failure modes if this boundary is violated

- Persisted ranked results drift from business truth because storage starts applying its own ordering or filtering.
- Search reports show a different “best” result than the runner selected.
- CLI summaries become a second ranking source and confuse downstream automation.

#### Migration notes from current implementation

- `search_reporting.py` already loads persisted artifacts to render best-search and comparison reports.
- `storage.py` already writes ranked-results CSVs.
- `cli.py` already surfaces `ranked_results_path`, `report_path`, and `search_report_path` when present.
- The current implementation is healthy as long as those modules remain consumers of authoritative search outputs rather than authors of search truth.

#### Open questions / deferred decisions

- Whether the ranked-results CSV should remain the canonical persisted search artifact or later be supplemented by a richer manifest is deferred.
  - Recommended default: keep the CSV as the persisted business artifact and add a manifest only if a future workflow needs more metadata.

#### Scenario: downstream layers display search results without redefining them

- GIVEN ranked search results are already authoritative
- WHEN storage, reporting, or CLI surfaces them
- THEN those layers SHALL display or persist the results only
- AND they SHALL NOT replace the search or ranking owners’ business semantics

### Requirement: `search.py` owns the supported strategy-family set consumed by search-adjacent workflows

`src/alphaforge/search.py` SHALL remain the canonical owner of the supported strategy-family set, and search-adjacent consumers SHALL derive that set from `SUPPORTED_STRATEGY_FAMILIES` instead of maintaining local copies.

#### Purpose

- Keep the named family list authoritative in one place.
- Prevent permutation diagnostics and CLI choices from drifting away from the family set already accepted by search and runner workflows.

#### Canonical owner

- `src/alphaforge/search.py` is the authoritative owner of `SUPPORTED_STRATEGY_FAMILIES`.
- `src/alphaforge/permutation.py` and `src/alphaforge/cli.py` are downstream consumers of that family set when they need to validate or expose supported strategy names.

#### Allowed responsibilities

- `search.py` MAY expose a small explicit tuple of supported family names.
- downstream consumers MAY import and reuse that tuple when their behavior must stay aligned with search-supported families.

#### Explicit non-responsibilities

- `permutation.py` MUST NOT define a second supported-family list for diagnostic strategy construction.
- `cli.py` MUST NOT hardcode a divergent supported-family list for `permutation-test`.

#### Inputs / outputs / contracts

- Input:
  - an explicit strategy-family name
- Output:
  - family-aligned search candidates or family-aligned consumer validation
- Contract rule:
  - any workflow that claims support for a search-supported strategy family must derive the family name set from `search.py`

#### Invariants

- The supported-family set has one authoritative definition.
- Search-adjacent workflows either support a derived subset intentionally or the full canonical set; they do not silently fork the naming contract.

### Requirement: validation-only custom-signal workflows are not search-space families

`src/alphaforge/search.py` SHALL reject `custom_signal` as a search-space family and SHALL NOT enumerate it as a grid-search candidate family.

#### Scenario: custom_signal is routed to research validation, not search

- GIVEN a caller asks `search.py` to build candidates for `custom_signal`
- WHEN search-space generation runs
- THEN AlphaForge SHALL raise a clear error
- AND the error SHALL indicate that `custom_signal` is validation-only rather than search-capable
- AND search-space generation SHALL NOT attempt to infer parameter-grid semantics for `signal.csv`

