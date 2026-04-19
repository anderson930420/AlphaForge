# experiment-runner-orchestration Specification

## Purpose
- Define the stable public runner boundary for AlphaForge.
- Keep workflow sequencing public and compatible while ensuring workflow bodies and shared runner helpers can evolve in narrower internal modules.

## Requirements
### Requirement: Experiment runner owns workflow orchestration only

`src/alphaforge/experiment_runner.py` SHALL remain the public runner façade for runtime workflow orchestration and SHALL NOT become the authoritative owner of schemas, persistence shape, analytics formulas, benchmark semantics, or report content.

#### Purpose

- Define `src/alphaforge/experiment_runner.py` as the authoritative owner of runtime workflow sequencing for single-run, search, validation, walk-forward, and search-report workflows.
- Prevent orchestration code from silently becoming the owner of schemas, persistence shape, analytics formulas, benchmark semantics, or report content.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` is the single authoritative owner of the public runner API and compatibility bundles.
- `src/alphaforge/runner_workflows.py` is the canonical owner of workflow-specific orchestration implementations.
- `src/alphaforge/runner_protocols.py` is the canonical owner of shared runner-only helpers such as default config assembly, strategy dispatch, split/fold generation, and validation metadata assembly.
- The orchestration jobs exposed publicly through the façade are:
  - single experiment workflow,
  - ranked search workflow,
  - validation workflow,
  - walk-forward workflow,
  - search-report workflow.

#### Allowed responsibilities

- `experiment_runner.py` MAY expose public runner functions and compatibility bundles used by CLI and tests.
- `runner_workflows.py` MAY sequence calls to authoritative lower-layer owners in runtime order.
- `runner_protocols.py` MAY materialize default `BacktestConfig` values, strategy dispatch, train/test split helpers, walk-forward fold generation, train-window sufficiency checks, and validation metadata assembly.
- `runner_workflows.py` MAY attach workflow-scoped metadata to result objects only under `metadata`.
- `runner_workflows.py` MAY decide whether persistence or report-generation side effects run based on workflow inputs.

#### Explicit non-responsibilities

- Must not own persisted artifact schemas, filenames, or output directory layout.
- Must not own in-memory result schema definitions.
- Must not own market-data schema validation or missing-data policy.
- Must not own strategy signal formulas.
- Must not own execution timing, trade extraction, turnover, or equity semantics.
- Must not own metric formulas, score formulas, or benchmark formulas.
- Must not own HTML structure, chart structure, or report-content formatting.
- Must not own parameter-grid generation or canonical parameter-validity semantics.

#### Inputs / outputs / contracts

- Inputs:
  - `DataSpec`
  - `StrategySpec`
  - `BacktestConfig`
  - search, validation, and walk-forward protocol parameters
- Upstream authoritative contracts consumed:
  - `load_market_data()` from `data_loader.py`
  - `build_strategy_specs()` from `search.py`
  - `run_backtest()` from `backtest.py`
  - `compute_metrics()` from `metrics.py`
  - `summarize_buy_and_hold()` from `benchmark.py`
  - persistence functions from `storage.py`
  - report-rendering functions from `report.py`
- Outputs:
  - `ExperimentResult`
  - `list[ExperimentResult]`
  - `ValidationResult`
  - `WalkForwardResult`
  - saved report paths returned from `report.py`

#### Invariants

- Every workflow entry point remains expressible as an ordered call graph over authoritative lower-layer owners.
- No workflow may redefine the shape of `ExperimentResult`, `ValidationResult`, or `WalkForwardResult`.
- Workflow-local metadata remains protocol-scoped and must not become a parallel schema authority.
- Strategy dispatch by `StrategySpec.name` remains orchestration-owned until explicitly reassigned by a later spec.

#### Cross-module dependencies

- Depends on `config.py` for defaults only.
- Depends on `schemas.py` for runtime contracts only.
- Depends on `data_loader.py` for market-data acceptance.
- Depends on `search.py` for strategy-spec generation.
- Depends on strategy modules for signal generation.
- Depends on `backtest.py`, `metrics.py`, `benchmark.py`, and `scoring.py` for domain semantics.
- Depends on `storage.py` for persistence.
- Depends on `report.py` for rendered reports.
- Is consumed by `cli.py` and workflow tests.

#### Failure modes if this boundary is violated

- Search output paths drift from saved artifacts because orchestration redefines naming already owned by `storage.py`.
- Validation and walk-forward summaries drift from runtime contracts because orchestration creates ad hoc result shapes.
- Reports disagree with stored metrics because orchestration starts recomputing analytics or benchmark values.
- Search-space behavior diverges between workflows because orchestration filters parameters independently of `search.py`.
- Future features accumulate in `experiment_runner.py` as implicit domain rules rather than explicit orchestration jobs.

#### Migration notes from current implementation

- `experiment_runner.py` now acts as a thin compatibility façade and delegates internal orchestration bodies to `runner_workflows.py`.
- Shared runner helpers such as strategy dispatch, default config resolution, split-by-ratio, train-window validation, validation metadata, and fold generation now live in `runner_protocols.py`.
- Search-report preparation continues to flow through `search_reporting.py`, while the runner layer keeps only the sequencing decision of whether report generation runs.
- Walk-forward aggregate-result policy continues to flow through `walk_forward_aggregation.py`.
- Single-run execution output pairing continues to use runner-local compatibility bundles rather than anonymous tuples.

#### Open questions / deferred decisions

- Whether search-report orchestration should consume in-memory frames or persisted CSVs once persistence and reporting boundaries are tightened further.
- Whether workflow-local metadata should later move to narrower typed structures.
- Whether strategy dispatch should move out of orchestration once multiple strategy families exist.
- Whether workflow-scoped naming such as `train_search`, `train_best`, `test_selected`, and `fold_{index:03d}` should remain runner-owned sequencing labels or be promoted into a narrower orchestration contract later.

#### Scenario: public runner facade delegates all non-orchestration semantics

- GIVEN a caller provides `DataSpec`, `StrategySpec`, and optional `BacktestConfig`
- WHEN `run_experiment()` executes
- THEN `experiment_runner.py` SHALL delegate to internal runner workflow implementations
- AND the workflow implementation SHALL call authoritative lower-layer owners for data loading, strategy execution, backtest execution, metric computation, scoring, benchmark summary creation, and optional persistence
- AND the public façade SHALL NOT define metric formulas, trade semantics, persisted artifact schemas, or report content locally

#### Scenario: Search workflow uses storage-owned artifact persistence

- GIVEN a caller runs a ranked search with `output_dir`
- WHEN `run_search()` persists ranked results and optional reports
- THEN `experiment_runner.py` SHALL delegate ranked-results artifact writing to `storage.py`
- AND `experiment_runner.py` SHALL delegate rendered report creation to `report.py`
- AND `experiment_runner.py` SHALL NOT define independent filenames, directory layout rules, or report HTML structure

#### Scenario: Validation and walk-forward protocols remain orchestration-scoped

- GIVEN a caller runs validation or walk-forward search
- WHEN `experiment_runner.py` splits market data and generates evaluation windows
- THEN those segmentation rules SHALL be treated as workflow protocol semantics owned by orchestration
- AND those rules SHALL NOT be treated as market-data schema rules, strategy semantics, or persisted artifact schema rules
