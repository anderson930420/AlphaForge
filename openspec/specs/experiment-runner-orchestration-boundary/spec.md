# Experiment Runner Orchestration Boundary Specification

## Purpose

- Define the canonical orchestration boundary for `src/alphaforge/experiment_runner.py`.
- Make workflow sequencing explicit for single-run execution, search execution, validation execution, walk-forward execution, and report workflow orchestration.
- Prevent `experiment_runner.py` from becoming the authoritative owner of domain rules already owned by `data_loader.py`, `search.py`, `backtest.py`, `metrics.py`, `benchmark.py`, `report.py`, `storage.py`, or `schemas.py`.
- Define the exact points where `experiment_runner.py` may assemble workflow-level metadata and result objects without redefining lower-layer schemas.

## Requirements

### Requirement: `experiment_runner.py` remains orchestration-only

`src/alphaforge/experiment_runner.py` SHALL coordinate workflows only and SHALL defer domain truth to the lower-level owners named by the architecture boundary map and the subprotocol boundary spec.

#### Scenario: Workflow sequencing does not redefine domain semantics

- **WHEN** the runner executes single-run, search, validation, walk-forward, or report flows
- **THEN** it SHALL sequence authoritative modules rather than own execution, search, scoring, persistence, or reporting truth locally

## Canonical owner

- `src/alphaforge/experiment_runner.py` is the authoritative owner of AlphaForge runtime workflow orchestration semantics.
- Within the current file, the following orchestration jobs are canonically owned here even if they remain in one module temporarily:
  - single experiment workflow orchestration,
  - search workflow orchestration,
  - validation workflow orchestration,
  - walk-forward workflow orchestration,
  - report workflow orchestration for search reports,
  - strategy implementation dispatch from `StrategySpec.name`.
- `experiment_runner.py` is not the canonical owner of any business rule, persisted artifact schema, market-data schema, metric formula, benchmark formula, or presentation schema used within those workflows.

## Allowed responsibilities

- Accept runtime request contracts built from `schemas.py` and CLI assembly.
- Materialize default `BacktestConfig` values from `config.py` only when a caller omits explicit runtime configuration.
- Call `load_market_data()` exactly once per top-level workflow input dataset unless a workflow intentionally operates on an already-sliced in-memory segment.
- Dispatch strategy construction from `StrategySpec.name` to the concrete strategy implementation.
- Sequence authoritative owners in this order where applicable:
  - load data,
  - derive strategy specs,
  - generate signals,
  - run backtest,
  - compute metrics,
  - compute score,
  - compute benchmark summary,
  - persist artifacts,
  - render or save reports.
- Construct `ExperimentResult`, `ValidationResult`, `WalkForwardFoldResult`, and `WalkForwardResult` values from authoritative lower-layer outputs without changing their schema definitions.
- Define workflow-local segmentation mechanics for:
  - train/test ratio splitting,
  - walk-forward fold generation,
  - train-window sufficiency checks,
  - top-N search-report curve selection.
- Attach workflow metadata that is explicitly workflow-scoped and not already owned by another module, such as:
  - train/test row counts,
  - fold counts,
  - train/test segment date bounds,
  - benchmark summary inclusion inside result metadata.
- Decide whether persistence or report-generation side effects occur based on runtime flags and presence of `output_dir`.

## Explicit non-responsibilities

- `experiment_runner.py` must not own the canonical market data schema or missing-data policy.
- `experiment_runner.py` must not own strategy interface semantics or strategy-specific signal formulas.
- `experiment_runner.py` must not own execution semantics such as position lag, turnover calculation, trade extraction, fee/slippage application, or equity-curve construction.
- `experiment_runner.py` must not own performance analytics semantics such as return, drawdown, Sharpe, turnover, win-rate, or trade-count formulas.
- `experiment_runner.py` must not own benchmark semantics such as buy-and-hold curve construction or benchmark drawdown logic.
- `experiment_runner.py` must not own search-space generation rules or parameter-grid validity rules beyond invoking the authoritative search owner and enforcing workflow-local train-window sufficiency.
- `experiment_runner.py` must not own persisted artifact schemas, filenames, output directory layout, or ranked-results column order.
- `experiment_runner.py` must not own HTML structure, chart construction, or report content formatting.
- `experiment_runner.py` must not define parallel dataclasses or ad hoc dictionaries that duplicate result schemas already defined in `schemas.py`, except for workflow-local metadata fields stored in `metadata`.
- `experiment_runner.py` must not introduce CLI-specific request parsing or CLI payload formatting.

## Inputs / outputs / contracts

- Inputs:
  - `DataSpec` from `schemas.py`
  - `StrategySpec` from `schemas.py`
  - `BacktestConfig` from `schemas.py` or omitted to trigger default assembly
  - workflow parameters for search, validation, and walk-forward execution
- Authoritative upstream contracts consumed:
  - market-data frames validated by `data_loader.py`
  - strategy contract from `strategy/base.py`
  - strategy specs from `search.py`
  - backtest outputs from `backtest.py`
  - metric reports from `metrics.py`
  - benchmark summaries from `benchmark.py`
  - persistence contracts from `storage.py`
  - report-rendering contracts from `report.py`
- Outputs:
  - `tuple[ExperimentResult, EquityCurveFrame, pd.DataFrame]` for single-run workflows
  - `list[ExperimentResult]` for ranked search workflows
  - `ValidationResult` for validation workflows
  - `WalkForwardResult` for walk-forward workflows
  - saved report paths only through calls to `report.py`
- Contract rules:
  - Any `ExperimentResult` created here must be constructed from authoritative lower-layer outputs and may only add workflow metadata under `metadata`.
  - Any saved artifact path attached to a result must come from `storage.py` or `report.py`, not from locally assembled path conventions outside those owners.
  - Any ranked results returned from search orchestration must already have passed the authoritative ranking filter in `scoring.rank_results()`.

## Invariants

- Every top-level workflow in `experiment_runner.py` must be expressible as an ordered call graph over authoritative lower-layer owners.
- No workflow may redefine the shape of `ExperimentResult`, `ValidationResult`, or `WalkForwardResult`.
- Search execution, validation protocol, and walk-forward protocol remain authoritative here until explicitly reassigned by a future boundary spec.
- Market-data splitting for validation and walk-forward execution is authoritative here only as workflow protocol, not as market-data schema logic.
- Train-window sufficiency checks are authoritative here only as workflow protocol guards for search/validation execution, not as strategy or search-space semantics.
- Report workflow orchestration may decide when to call reporting functions, but `report.py` remains authoritative for rendered content and saved report file behavior.
- Strategy dispatch by `StrategySpec.name` remains authoritative here until a future strategy registry spec reassigns ownership.

## Cross-module dependencies

- Depends on `config.py` only for default value injection when callers omit `BacktestConfig`.
- Depends on `data_loader.py` for authoritative market-data acceptance and cleaning.
- Depends on `search.py` for authoritative strategy-spec generation from parameter grids.
- Depends on `strategy/ma_crossover.py` and `strategy/base.py` for strategy dispatch and signal generation.
- Depends on `backtest.py` for execution semantics.
- Depends on `metrics.py` and `scoring.py` for analytics and ranking.
- Depends on `benchmark.py` for benchmark summaries attached to workflow results.
- Depends on `storage.py` for persisted artifact schemas and directory layout.
- Depends on `report.py` for best-run and search-report generation.
- Depends on `schemas.py` for all runtime result object classes.
- Downstream consumers:
  - `cli.py` consumes all top-level workflow entry points.
  - tests consume workflow outputs and persisted side effects.

## Failure modes if this boundary is violated

- If `experiment_runner.py` starts redefining ranked-results columns instead of delegating to `storage.py`, search CSV outputs and CLI summaries will drift.
- If `experiment_runner.py` starts recomputing metrics or benchmark values, stored summaries, result metadata, and reports will disagree about the same run.
- If `experiment_runner.py` introduces strategy-parameter filtering rules independent of `search.py` or strategy construction, valid search spaces will differ by workflow entry point.
- If `experiment_runner.py` owns report path naming separately from `report.py` and `storage.py`, generated files and advertised file paths will diverge.
- If workflow-local metadata expands into ad hoc schema fields outside `schemas.py`, downstream serialization and tests will need workflow-specific parsing branches.
- If `experiment_runner.py` absorbs CLI parsing concerns, runtime orchestration and request assembly will become coupled and block non-CLI callers from reusing workflows cleanly.
- If `experiment_runner.py` becomes the only place where validation or walk-forward semantics are discoverable, execution semantics will be hidden in implementation details instead of explicit spec language.

## Migration notes from current implementation

- `build_strategy()` currently lives in `experiment_runner.py`.
  - Temporary status: allowed as orchestration-owned dispatch.
  - Migration trigger: add a new authoritative strategy-family registry only when more than one strategy family exists and dispatch semantics become reusable outside orchestration.
- `_validate_train_windows()` currently guards train segments using the maximum requested `long_window`.
  - Canonical interpretation: workflow-local protocol guard, not strategy semantics.
- `_split_market_data_by_ratio()` and `_generate_walk_forward_folds()` currently define validation and walk-forward segmentation.
  - Canonical interpretation: protocol ownership stays here until moved into a dedicated validation protocol owner by explicit spec.
- `_save_best_search_report()` and `_save_search_comparison_report()` currently mix orchestration with loading persisted artifacts back from disk.
  - Temporary status: allowed as report workflow orchestration.
  - Required constraint: they must not redefine HTML content, artifact naming, or report schema.
- `ExperimentResult.metadata` currently carries `missing_data_policy` and `benchmark_summary`.
  - Canonical interpretation: metadata inclusion is orchestration-owned, but the meaning of the values remains owned by `data_loader.py` and `benchmark.py`.

## Open questions / deferred decisions

- Whether report workflow orchestration should keep reading persisted CSVs back from disk for report generation, or instead pass in-memory frames directly when available.
- Whether validation protocol and walk-forward protocol should remain in `experiment_runner.py` if additional protocol families are added.
- Whether workflow-local metadata should be narrowed further so `ExperimentResult.metadata` does not become a generic escape hatch for unowned schema fields.
- Whether strategy dispatch should remain a file-local helper once non-MA strategies are introduced.
