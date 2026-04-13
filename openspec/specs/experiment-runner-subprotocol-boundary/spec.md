# experiment-runner-subprotocol-boundary Specification

## Purpose
TBD - created by archiving change formalize-experiment-runner-subprotocol-boundary. Update Purpose after archive.
## Requirements
### Requirement: `experiment_runner.py` is the canonical owner of workflow protocol orchestration only

`src/alphaforge/experiment_runner.py` SHALL be the single authoritative owner of AlphaForge workflow protocol orchestration, including the internal subprotocols for single-run, search execution, validate-search, walk-forward, and optional persistence/report triggering.

#### Purpose

- Keep the runner as the orchestration boundary that sequences authoritative owners without becoming a super-module.
- Make the protocol seams explicit so future refactors can move internals without changing domain truth.
- Prevent the runner from absorbing search-space, ranking, execution, storage, or report ownership under the excuse of coordination.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` is the only authoritative owner of workflow protocol orchestration.
- The runner is authoritative for protocol sequencing, not for the business meaning of the data it passes through.
- `src/alphaforge/search.py` remains authoritative for search-space generation.
- `src/alphaforge.scoring.py` remains authoritative for ranking and best-candidate semantics.
- `src/alphaforge.backtest.py` remains authoritative for execution semantics.
- `src/alphaforge.storage.py` remains authoritative for artifact layout and persisted artifact refs.
- `src/alphaforge.report.py` remains authoritative for report-view-model assembly and rendering semantics.

#### Allowed responsibilities

- `experiment_runner.py` MAY:
  - accept request DTOs assembled by CLI or other callers,
  - load market data through the canonical loader,
  - instantiate or route to strategy implementations from canonical strategy specs,
  - sequence candidate generation, execution, scoring, persistence, and reporting in the correct order for each workflow,
  - aggregate authoritative outputs into runner-local protocol receipts or result bundles,
  - decide whether a workflow branch persists artifacts or triggers reporting based on runtime flags and output directory presence.

#### Explicit non-responsibilities

- `experiment_runner.py` MUST NOT own execution semantics, market-data acceptance semantics, search-space generation, ranking semantics, storage layout truth, report-view-model semantics, metrics semantics, benchmark semantics, or CLI request parsing.
- `experiment_runner.py` MUST NOT redefine what a candidate is, what the best candidate is, or how scores are computed.
- `experiment_runner.py` MUST NOT redefine artifact filenames, report input meaning, or downstream presentation semantics.
- `experiment_runner.py` MUST NOT become the hidden owner of workflow business truth just because it coordinates multiple subprotocols.

#### Inputs / outputs / contracts

- Inputs:
  - CLI-assembled request DTOs or direct runtime specs
  - loader-accepted market data
  - canonical candidate lists from `search.py`
  - canonical ranking outputs from `scoring.py`
  - canonical execution outputs from `backtest.py`, `metrics.py`, and `benchmark.py`
  - canonical artifact refs from `storage.py`
  - canonical report inputs from `report.py`
- Outputs:
  - workflow protocol receipts or aggregates such as `ExperimentExecutionOutput`, `SearchExecutionOutput`, `ValidationExecutionOutput`, and `WalkForwardResult`
  - optional persistence refs
  - optional report refs
- Contract rule:
  - runner outputs are protocol-level aggregates over authoritative owners, not new domain contracts

#### Invariants

- The runner may coordinate many modules, but it must not become the owner of their meanings.
- Every runner subprotocol must be expressible as an ordered call graph over authoritative owners.
- Any data surfaced by the runner as a result, receipt, or summary must be traceable to an upstream owner.
- If the same fact already has an owner upstream, the runner may forward it but must not reinterpret it.

#### Cross-module dependencies

- `cli.py` supplies request DTOs but does not own protocol execution.
- `data_loader.py` supplies accepted market data.
- `search.py` supplies candidates.
- `scoring.py` supplies ranked results and best-candidate selection.
- `backtest.py`, `metrics.py`, and `benchmark.py` supply executed domain facts.
- `storage.py` supplies artifact refs and persisted summaries.
- `report.py` supplies report inputs and rendered output behavior.

#### Failure modes if this boundary is violated

- The runner turns into a super-module that quietly owns search, scoring, execution, storage, or report truth.
- Validation and walk-forward flows drift because their protocol logic is not explicitly separated from plain search.
- Runner-local receipts start looking like alternate schemas for upstream facts, making tests and refactors fragile.
- Persistence and report triggering become business rules instead of sequencing decisions.

#### Migration notes from current implementation

- `experiment_runner.py` already sequences load → strategy dispatch → execution → metrics → score → benchmark → persistence/report triggering.
- The current module also already exposes distinct public entry points for run, search, validate-search, and walk-forward.
- The current implementation is operationally healthy, but the internal protocol boundaries are still implicit enough that the file can continue to accumulate meaning.
- This spec freezes the separation so future changes do not blur protocol orchestration with domain ownership.

#### Open questions / deferred decisions

- Whether internal protocol receipts should eventually move into separate private dataclasses or remain inside `experiment_runner.py` is deferred.
  - Recommended default: keep the public workflow bundles here while they continue to act as orchestration receipts rather than domain truth.
- Whether persistence/report triggering should remain in the runner or split into small internal protocol helpers later is deferred.
  - Recommended default: keep them as runner subprotocols until the codebase needs a narrower split for reuse.
- Whether strategy dispatch should remain runner-owned or move into a dedicated registry when more strategy families exist is deferred.
  - Recommended default: keep dispatch in the runner for now because it is protocol coordination, not strategy semantics ownership.

#### Scenario: runner outputs remain protocol receipts

- GIVEN a workflow completes through the runner
- WHEN the runner returns its workflow bundle
- THEN the returned object SHALL be a protocol receipt or aggregate over upstream owners
- AND it SHALL NOT be treated as a new source of domain truth

### Requirement: the runner SHALL expose distinct subprotocols for single-run, search, validate-search, and walk-forward workflows

`src/alphaforge/experiment_runner.py` SHALL decompose its orchestration into distinct subprotocols for single-run, search-execution, validate-search, and walk-forward behavior.

#### Purpose

- Make each workflow path separately understandable and separately testable.
- Prevent one runner flow from silently inheriting the semantics of another flow.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` is authoritative for the existence and sequencing of these subprotocols.
- The semantics used inside each subprotocol remain owned by the canonical upstream modules they call.

#### Allowed responsibilities

- Each subprotocol MAY:
  - collect its own workflow-local metadata,
  - request persistence and report triggering when the workflow requires it,
  - reuse shared candidate execution helpers if they do not redefine protocol meaning,
  - return a workflow-specific protocol bundle.

#### Explicit non-responsibilities

- No subprotocol MAY redefine search-space generation, ranking, execution semantics, persistence layout, or report-view-model semantics.
- No subprotocol MAY silently borrow protocol rules from another workflow path unless the contract explicitly says the rule is shared.

#### Inputs / outputs / contracts

- Subprotocol family:
  - single-run protocol
  - search-execution protocol
  - validate-search protocol
  - walk-forward protocol
  - persistence/report-triggering protocol
- Outputs:
  - runner-local bundles that describe the protocol outcome for each workflow

#### Invariants

- Each protocol has a purpose, upstream inputs, and allowed outputs that are distinct from the others.
- Shared lower-layer owners remain shared; only the protocol flow changes by workflow.
- A protocol may reuse other protocols’ outputs, but it must not become another owner of their business facts.

#### Cross-module dependencies

- Single-run and search-execution subprotocols both call the execution, scoring, storage, and report owners.
- Validate-search reuses search-execution outputs and train/test protocol helpers.
- Walk-forward reuses search-execution and validation-like slicing logic per fold.

#### Failure modes if this boundary is violated

- Validation and walk-forward become indistinguishable from plain search, which makes protocol-specific bugs hard to isolate.
- A change to one workflow unexpectedly alters another because the runner never named the shared or distinct parts of the protocol.
- Internal helper reuse becomes accidental, leading to duplicated or conflicting orchestration branches.

#### Migration notes from current implementation

- The runner already has separate public functions for run, search, validate-search, and walk-forward.
- Those functions are already distinct call graphs, but their internal protocol boundaries are not yet explicitly frozen in spec form.
- This requirement makes the decomposition contractual rather than incidental.

#### Open questions / deferred decisions

- Whether future workflows need additional named subprotocols beyond the four core ones is deferred.
  - Recommended default: add new subprotocols only when a workflow has materially different protocol flow.

#### Scenario: validate-search remains distinct from plain search

- GIVEN a workflow performs a train/test validation split
- WHEN the runner executes the validation path
- THEN it SHALL use the validate-search subprotocol
- AND it SHALL NOT collapse that flow into plain search

### Requirement: single-run protocol coordinates one end-to-end execution without owning downstream truth

The runner’s single-run protocol SHALL coordinate a single authoritative execution chain while treating all downstream facts as upstream-owned outputs.

#### Purpose

- Keep the single-run path useful for CLI and programmatic callers while preventing it from growing into a second owner of execution, metrics, benchmark, storage, or report semantics.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` owns the single-run protocol sequencing only.
- `data_loader.py`, `strategy/base.py`, `backtest.py`, `metrics.py`, `benchmark.py`, `storage.py`, and `report.py` own the meanings of the facts the protocol passes through.

#### Allowed responsibilities

- The single-run protocol MAY:
  - load accepted market data,
  - instantiate the selected strategy from a `StrategySpec`,
  - invoke strategy signal generation,
  - invoke backtest execution,
  - invoke metric computation,
  - compute or consume benchmark summaries,
  - persist artifacts when `output_dir` is present,
  - build report inputs and trigger report generation when requested,
  - aggregate the above into a runner-local execution bundle.

#### Explicit non-responsibilities

- The single-run protocol MUST NOT redefine signal interpretation, trade extraction, fee/slippage application, metrics formulas, benchmark formulas, storage layout, or report-view-model meaning.
- The single-run protocol MUST NOT invent its own benchmark or metrics truth before surfacing it.
- The single-run protocol MUST NOT treat the runner bundle as a replacement for the authoritative result objects it aggregates.

#### Inputs / outputs / contracts

- Inputs:
  - `DataSpec`
  - `StrategySpec`
  - `BacktestConfig`
  - optional output directory and experiment label
- Outputs:
  - runner-local single-run bundle such as `ExperimentExecutionOutput`
  - authoritative result objects and receipts from upstream owners
- Contract rule:
  - the runner bundle is a protocol receipt containing upstream facts and workflow refs, not a new business schema

#### Invariants

- The runner may assemble the single-run chain, but the semantics of the numbers come from upstream owners.
- If persistence and reporting are requested, those steps happen after authoritative execution and summary assembly.
- The runner must not need to infer any canonical artifact or report meaning to complete the protocol.

#### Cross-module dependencies

- `data_loader.py` provides accepted market data.
- `strategy/base.py` and concrete strategy classes provide strategy behavior.
- `backtest.py`, `metrics.py`, and `benchmark.py` provide authoritative facts.
- `storage.py` may persist artifacts.
- `report.py` may render the report input assembled from upstream facts.

#### Failure modes if this boundary is violated

- Single-run output starts mixing protocol receipts with runner-invented business truths.
- Report generation or persistence becomes impossible to reason about because the runner is carrying too much meaning.
- A change to execution or metrics semantics requires editing runner code that should merely consume those owners.

#### Migration notes from current implementation

- `run_experiment_with_artifacts()` already coordinates load, strategy dispatch, execution, metrics, benchmark, persistence, and report input assembly.
- `ExperimentExecutionOutput` already acts as a runner-local bundle rather than a domain model.
- This spec makes that bundle explicitly a protocol receipt and keeps the underlying facts owned upstream.

#### Open questions / deferred decisions

- Whether the single-run bundle should remain a separate public dataclass or eventually be replaced by a smaller runner result is deferred.
  - Recommended default: keep it while CLI and tests rely on the explicit protocol receipt.

#### Scenario: single-run protocol returns a receipt, not a new domain truth

- GIVEN a single-run workflow completes
- WHEN the runner returns its bundle
- THEN the bundle SHALL contain upstream-owned facts and workflow refs
- AND it SHALL NOT redefine execution, metrics, benchmark, or report semantics

### Requirement: search-execution protocol consumes canonical candidates and canonical rankings

The runner’s search-execution protocol SHALL execute candidates provided by `search.py` and rank the resulting executions through `scoring.py` without taking ownership of either contract.

#### Purpose

- Keep plain search as a workflow over authoritative candidate and ranking owners.
- Prevent the runner from becoming the source of candidate enumeration or best-candidate truth.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` owns the search-execution protocol.
- `src/alphaforge/search.py` owns the candidate list.
- `src/alphaforge/scoring.py` owns the ranking order and thresholds.

#### Allowed responsibilities

- The search-execution protocol MAY:
  - request the ordered candidate list from `search.py`,
  - execute each candidate through the single-run execution chain,
  - collect each executed result,
  - call `scoring.rank_results()` to obtain the canonical ranking,
  - persist the ranked results through `storage.py`,
  - trigger best-report and comparison-report generation when requested,
  - return a search bundle such as `SearchExecutionOutput`.

#### Explicit non-responsibilities

- The search-execution protocol MUST NOT generate candidates itself.
- The search-execution protocol MUST NOT define ranking formulas or threshold rules.
- The search-execution protocol MUST NOT alter the meaning of the candidate list or the ranked result order.
- The search-execution protocol MUST NOT own persisted output names or report input semantics.

#### Inputs / outputs / contracts

- Inputs:
  - `DataSpec`
  - parameter grid
  - `BacktestConfig`
  - optional drawdown/trade thresholds
  - optional output directory and experiment name
- Outputs:
  - ranked `ExperimentResult` list
  - ranked-results storage refs
  - optional report refs
  - runner-local search bundle such as `SearchExecutionOutput`
- Contract rule:
  - the runner bundle is a protocol receipt over executed and ranked results, not a second ranking owner

#### Invariants

- Search-execution always consumes the canonical candidate list and canonical ranking output.
- The runner may control when search persistence and report triggering happen, but it may not change what the ranking means.
- The same candidate and score inputs should produce the same ranked outputs regardless of who called the runner.

#### Cross-module dependencies

- `search.py` provides candidates.
- `strategy/*` construct and validate the actual strategy instance for each candidate.
- `backtest.py`, `metrics.py`, and `benchmark.py` provide per-candidate facts.
- `scoring.py` ranks the results.
- `storage.py` persists ranked outputs.
- `report.py` renders best and comparison reports from explicit inputs.

#### Failure modes if this boundary is violated

- Search results diverge because the runner inserts its own candidate rules or selection logic.
- Best-candidate truth becomes inconsistent across runner, CLI, and reporting paths.
- Persisted ranked results no longer match the canonical ranking owner’s order.

#### Migration notes from current implementation

- `run_search_with_details()` already obtains candidates from `search.py`, executes them, and ranks them through `scoring.rank_results()`.
- It also already persists ranked results and may trigger reports based on `generate_best_report`.
- This spec freezes that split and prevents the runner from inheriting candidate or ranking ownership.

#### Open questions / deferred decisions

- Whether the search bundle should expose additional protocol receipts for filtering counts or rejection reasons is deferred.
  - Recommended default: keep only facts that are already authoritative and necessary for downstream workflow consumers.

#### Scenario: search execution uses canonical candidates and canonical ranking

- GIVEN a parameter grid and a market dataset
- WHEN the runner executes search
- THEN it SHALL consume the ordered candidate list from `search.py`
- AND it SHALL consume the ranked output from `scoring.py`
- AND it SHALL NOT redefine either contract locally

### Requirement: validate-search protocol is a runner-owned train/test orchestration over canonical search and ranking outputs

The validate-search protocol SHALL coordinate train/test search reuse as a distinct runner subprotocol without redefining plain search or scoring semantics.

#### Purpose

- Make validation behavior explicit so it does not become a loosely defined extension of plain search.
- Keep the validation split, train-only ranking reuse, and held-out test evaluation clearly orchestration-owned.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` owns the validate-search protocol.
- `src/alphaforge.search.py` and `src/alphaforge.scoring.py` remain authoritative for candidate and ranking semantics.
- `src/alphaforge.backtest.py`, `src/alphaforge.metrics.py`, and `src/alphaforge.benchmark.py` remain authoritative for execution and analytics semantics.

#### Allowed responsibilities

- The validate-search protocol MAY:
  - split accepted market data into train and test segments,
  - validate train-window sufficiency as a workflow guard,
  - run search on the train segment using the canonical search and ranking owners,
  - choose the top-ranked train candidate,
  - rerun the selected candidate on the held-out test segment,
  - persist validation outputs,
  - aggregate validation metadata and summary refs into a `ValidationResult` and/or runner-local validation bundle.

#### Explicit non-responsibilities

- The validate-search protocol MUST NOT redefine search-space generation or ranking truth.
- The validate-search protocol MUST NOT redefine what makes a candidate valid.
- The validate-search protocol MUST NOT own benchmark or metrics semantics.
- The validate-search protocol MUST NOT turn train/test split logic into market-data schema logic.
- The validate-search protocol MUST NOT use a different best-candidate rule than the canonical scoring owner.

#### Inputs / outputs / contracts

- Inputs:
  - `DataSpec`
  - parameter grid
  - split ratio
  - `BacktestConfig`
  - optional persistence/report flags
- Outputs:
  - `ValidationResult`
  - optional validation summary ref
  - optional train-ranked-results ref
  - workflow metadata such as row counts and date bounds
- Contract rule:
  - validation output is a protocol aggregate over canonical search/ranking outputs plus held-out test execution facts

#### Invariants

- Validation reuses plain search semantics rather than redefining them.
- The held-out test run must use the selected candidate from the canonical ranking owner.
- Validation-specific metadata is workflow-scoped only and must not replace upstream facts.

#### Cross-module dependencies

- `data_loader.py` supplies accepted data.
- `search.py` supplies candidates.
- `scoring.py` supplies train ranking and best-candidate selection.
- `backtest.py`, `metrics.py`, and `benchmark.py` supply execution and test facts.
- `storage.py` persists validation outputs.
- `report.py` renders validation-facing report inputs if requested.

#### Failure modes if this boundary is violated

- Validation picks a different best candidate than plain search because the runner re-ranks differently.
- Train/test split rules become hidden business semantics rather than protocol guards.
- Validation summaries drift from the canonical search and scoring owners.

#### Migration notes from current implementation

- `run_validate_search()` already performs a split, runs train search, selects the top-ranked candidate, reruns on the test segment, and persists validation output.
- The current behavior is aligned with the intended subprotocol; the missing piece is the explicit contract that says those are protocol steps, not new semantic owners.

#### Open questions / deferred decisions

- Whether the validation protocol should return a distinct private runner receipt in addition to `ValidationResult` is deferred.
  - Recommended default: keep the current public result and add only if future protocol metadata needs a clearer home.

#### Scenario: validation reuses canonical search outputs on train and held-out data

- GIVEN a validation split and a parameter grid
- WHEN the runner executes validate-search
- THEN it SHALL search the train segment using canonical search semantics
- AND it SHALL evaluate the chosen candidate on the held-out segment without redefining ranking

### Requirement: walk-forward protocol coordinates fold-based search reuse and fold-level aggregation

The walk-forward protocol SHALL coordinate fold-based search reuse and fold-level aggregation as a distinct runner subprotocol.

#### Purpose

- Keep walk-forward behavior separate from plain validation so fold sequencing remains explicit.
- Prevent the runner from turning walk-forward into a second owner of search or scoring truth.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` owns the walk-forward protocol.
- `src/alphaforge.search.py` and `src/alphaforge.scoring.py` remain authoritative for search and ranking semantics.
- `src/alphaforge.backtest.py`, `src/alphaforge.metrics.py`, and `src/alphaforge.benchmark.py` remain authoritative for execution and analytics semantics.
- `src/alphaforge.walk_forward_aggregation.py` remains authoritative for fold-aggregation calculations if it is present as a dedicated helper owner.

#### Allowed responsibilities

- The walk-forward protocol MAY:
  - generate fold/window boundaries,
  - slice market data per fold,
  - run search on each train fold using canonical search and ranking owners,
  - select the fold’s top-ranked candidate,
  - execute the selected candidate on the corresponding test fold,
  - aggregate fold-level results and benchmark summaries,
  - persist fold-level and walk-forward summary artifacts,
  - surface a `WalkForwardResult` with workflow metadata.

#### Explicit non-responsibilities

- The walk-forward protocol MUST NOT redefine candidate enumeration or ranking.
- The walk-forward protocol MUST NOT redefine execution semantics or fold-level analytics semantics.
- The walk-forward protocol MUST NOT replace `walk_forward_aggregation.py` if that module owns fold aggregation semantics.
- The walk-forward protocol MUST NOT become a second search owner just because it repeats search per fold.

#### Inputs / outputs / contracts

- Inputs:
  - `DataSpec`
  - parameter grid
  - train size
  - test size
  - step size
  - `BacktestConfig`
  - optional persistence/report flags
- Outputs:
  - `WalkForwardResult`
  - fold-level protocol receipts and summary refs
  - aggregate test and benchmark metrics
- Contract rule:
  - walk-forward output is a fold-structured protocol aggregate, not an alternate search contract

#### Invariants

- Each fold reuses the same canonical search and ranking owners.
- Fold aggregation may summarize results, but it may not create a new search truth.
- Walk-forward protocol differences from validation are sequencing and aggregation, not ownership of search or scoring semantics.

#### Cross-module dependencies

- `data_loader.py` supplies accepted data.
- `search.py` supplies fold-local candidates.
- `scoring.py` supplies fold-local ranking and best-candidate selection.
- `backtest.py`, `metrics.py`, and `benchmark.py` supply fold execution facts.
- `storage.py` persists walk-forward outputs.
- `report.py` may render fold or aggregate report inputs if requested.

#### Failure modes if this boundary is violated

- Walk-forward behaves differently from fold to fold because the runner redefines candidate or ranking truth locally.
- Fold aggregation becomes a second analytics owner and diverges from the dedicated aggregation helper.
- Validation and walk-forward become hard to compare because the runner’s protocol semantics are not explicit.

#### Migration notes from current implementation

- `run_walk_forward_search()` already loops over folds, searches each train fold, selects the top-ranked candidate, executes the test fold, aggregates metrics, and persists the result.
- The current implementation uses separate fold generation and aggregate helpers, which is consistent with this boundary.
- The spec formalizes that these are protocol steps, not new search or ranking ownership.

#### Open questions / deferred decisions

- Whether fold-generation helpers should remain inside the runner or move into a dedicated fold-protocol helper module later is deferred.
  - Recommended default: keep them in the runner until a second fold-based workflow needs reuse.

#### Scenario: walk-forward remains fold-based orchestration

- GIVEN a train/test window specification
- WHEN the runner executes walk-forward
- THEN it SHALL search and rank within each fold using canonical owners
- AND it SHALL aggregate fold outputs without redefining search or scoring semantics

### Requirement: strategy dispatch is runner-owned protocol routing only

The runner SHALL route to strategy implementations by canonical strategy spec without owning strategy semantics.

#### Purpose

- Keep strategy selection a workflow concern while preserving strategy ownership in the strategy layer.
- Prevent runner dispatch from becoming a hidden strategy registry owner.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` owns strategy dispatch as protocol routing.
- `src/alphaforge/strategy/base.py` owns the interface contract.
- `src/alphaforge/strategy/ma_crossover.py` owns MA-specific behavior and parameter validity.

#### Allowed responsibilities

- The runner MAY:
  - inspect `StrategySpec.name`,
  - route to the correct strategy implementation for the current supported family,
  - construct the concrete strategy object,
  - raise a workflow error when the strategy family is unsupported.

#### Explicit non-responsibilities

- The runner MUST NOT own strategy semantics, signal meaning, or family-specific validity.
- The runner MUST NOT become the canonical strategy registry unless a future spec explicitly reassigns that ownership.
- The runner MUST NOT treat strategy dispatch as a reason to reinterpret candidate meaning.

#### Inputs / outputs / contracts

- Inputs:
  - `StrategySpec`
- Outputs:
  - concrete strategy instance
- Contract rule:
  - strategy dispatch is a protocol step, not a business-rule owner

#### Invariants

- The runner can choose a strategy implementation, but the strategy implementation owns what the strategy means.
- Unsupported strategies are protocol failures, not new domain semantics.

#### Cross-module dependencies

- `search.py` supplies candidate `StrategySpec` values.
- `strategy/base.py` and concrete strategies supply the actual behavior.
- `backtest.py` consumes the strategy’s generated signals.

#### Failure modes if this boundary is violated

- Runner dispatch turns into a hidden strategy registry with its own semantics.
- Strategy validity gets split between dispatch and constructor logic.
- Adding a new strategy family requires editing runner logic in ways that should belong in the strategy layer.

#### Migration notes from current implementation

- `build_strategy()` currently dispatches the MA crossover implementation based on `StrategySpec.name`.
- This is already clearly protocol routing, but it should remain explicitly non-semantic.

#### Open questions / deferred decisions

- Whether a dedicated strategy registry owner should eventually replace the file-local helper is deferred.
  - Recommended default: keep runner dispatch until more than one strategy family makes a registry useful.

#### Scenario: strategy routing does not redefine strategy meaning

- GIVEN a `StrategySpec`
- WHEN the runner dispatches strategy construction
- THEN it SHALL route to the correct implementation only
- AND it SHALL NOT alter the strategy’s semantic rules

### Requirement: persistence and report triggering are runner protocol steps, not layout or view-model ownership

The runner SHALL be allowed to trigger persistence and report generation as protocol steps, but it SHALL not own storage layout or report view-model semantics.

#### Purpose

- Separate sequencing from meaning so the runner can decide when side effects happen without deciding what those side effects mean.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` owns the decision to trigger persistence or reporting as part of workflow completion.
- `src/alphaforge.storage.py` owns persisted artifact layout and refs.
- `src/alphaforge.report.py` owns report input meaning and rendering.

#### Allowed responsibilities

- The runner MAY:
  - pass authoritative execution or ranking outputs to storage helpers,
  - pass storage refs and authoritative domain facts to report helpers,
  - request report generation after persistence or summary assembly,
  - surface returned refs in runner-level bundles.

#### Explicit non-responsibilities

- The runner MUST NOT define artifact filenames, directory trees, or storage truth.
- The runner MUST NOT reconstruct report inputs or report links from display-only refs.
- The runner MUST NOT own report content, chart composition, or report-view-model semantics.

#### Inputs / outputs / contracts

- Inputs:
  - authoritative results and summaries from upstream owners
  - optional output directory and report flags
- Outputs:
  - storage refs
  - report refs
  - protocol receipts that contain those refs
- Contract rule:
  - the runner may decide sequencing, but the meaning of the persisted or rendered output remains owned elsewhere

#### Invariants

- Sequencing is protocol-owned; filenames and report schemas are not.
- Runner bundles may carry refs returned by storage or report owners, but they may not become a second source of layout truth.
- Persistence/report triggering should be deterministic for a given workflow and flag set.

#### Cross-module dependencies

- `storage.py` writes canonical persisted artifacts.
- `report.py` writes rendered reports from explicit inputs.
- `search_reporting.py` may continue to act as a report workflow helper as long as it remains downstream of report ownership.

#### Failure modes if this boundary is violated

- Runner-triggered files drift from storage-owned layout rules.
- Report triggering starts carrying hidden report semantics in the runner bundle.
- Protocol bundles become confusing because they mix sequencing refs with layout truth.

#### Migration notes from current implementation

- The runner already decides whether to call persistence and report helpers based on `output_dir` and flags such as `generate_best_report`.
- That behavior is healthy as long as the runner only controls sequencing.
- The current output bundles already surface refs that came from storage or report owners, which is acceptable only if those refs remain downstream facts.

#### Open questions / deferred decisions

- Whether best-report and comparison-report generation should stay in search-report helpers or be invoked through a future protocol helper is deferred.
  - Recommended default: keep the sequencing in the runner while the storage and report owners remain separate.

#### Scenario: runner triggers persistence without owning layout

- GIVEN a workflow completes and `output_dir` is present
- WHEN the runner triggers persistence
- THEN it SHALL call the storage owner
- AND it SHALL NOT invent filenames or directory layout itself

### Requirement: runner outputs remain protocol aggregates over authoritative owners

Runner outputs in AlphaForge SHALL be protocol aggregates or receipts over authoritative upstream facts, workflow refs, and presentation-adjacent refs, not new domain contracts.

#### Purpose

- Make it obvious which parts of runner outputs are facts from upstream owners and which parts are workflow receipts or presentation refs.
- Prevent public runner bundles from becoming alternate data models with ambiguous ownership.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` owns the runner output bundle shapes.
- `src/alphaforge.schemas.py` owns the authoritative runtime result contracts contained inside them.

#### Allowed responsibilities

- Runner outputs MAY contain:
  - authoritative domain facts from `ExperimentResult`, `ValidationResult`, `WalkForwardResult`, and related runtime objects,
  - workflow metadata such as row counts, fold counts, and train/test bounds,
  - storage refs such as artifact paths,
  - report refs such as generated HTML paths,
  - protocol receipts describing which subprotocol completed.

#### Explicit non-responsibilities

- Runner outputs MUST NOT become a new owner of execution, ranking, storage, or report truth.
- Runner outputs MUST NOT be treated as a substitute for the upstream contracts they aggregate.
- Runner outputs MUST NOT hide which fields are workflow refs versus upstream facts.

#### Inputs / outputs / contracts

- Runner output families:
  - `ExperimentExecutionOutput`
  - `SearchExecutionOutput`
  - `ValidationExecutionOutput`
  - `WalkForwardResult`
- Output classification:
  - domain facts: upstream runtime results
  - workflow refs: storage and report paths
  - presentation-adjacent refs: display labels or report names when present

#### Invariants

- Runner outputs are stable protocol receipts for callers, not a replacement for canonical owners.
- The same upstream fact may appear in the runner bundle and in downstream persistence/report outputs, but the ownership remains upstream.
- If a field is only useful for protocol coordination, it must not be elevated into domain truth.

#### Cross-module dependencies

- `cli.py` consumes runner bundles and prints derived payloads.
- `storage.py` consumes runner outputs for persistence.
- `report.py` consumes runner outputs or their extracted facts for rendering.

#### Failure modes if this boundary is violated

- Public runner objects start behaving like alternate domain models.
- Workflow receipts become impossible to interpret because domain facts and protocol refs are mixed without classification.
- Tests become fragile because they have to infer which runner fields are authoritative and which are incidental.

#### Migration notes from current implementation

- `ExperimentExecutionOutput`, `SearchExecutionOutput`, and `ValidationExecutionOutput` already exist as runner-local bundles.
- `ExperimentExecutionOutput` currently mixes a domain result, execution frames, a report input, and an optional receipt, which is acceptable only if it is understood as a protocol aggregate.
- `SearchExecutionOutput` and `ValidationExecutionOutput` already carry refs that are clearly workflow receipts rather than domain truth.
- This spec freezes that interpretation so future changes do not accidentally promote protocol fields into canonical business semantics.

#### Open questions / deferred decisions

- Whether `WalkForwardResult` should eventually gain a runner-local wrapper analogous to the search and validation bundles is deferred.
  - Recommended default: keep the existing runtime result contract unless a distinct protocol receipt becomes necessary.

#### Scenario: runner bundles are protocol receipts, not alternate schemas

- GIVEN a caller receives a runner output bundle
- WHEN the caller inspects its fields
- THEN the caller SHALL treat the bundle as a protocol receipt over upstream owners
- AND the caller SHALL NOT treat it as an alternate canonical contract for execution, ranking, storage, or reporting

