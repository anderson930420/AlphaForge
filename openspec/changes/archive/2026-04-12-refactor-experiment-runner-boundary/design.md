# Design: refactor-experiment-runner-boundary

## Canonical ownership mapping

- `experiment_runner.py`
  - authoritative for workflow sequencing and workflow protocol guards
  - not authoritative for schemas, persistence shape, analytics formulas, or report content
- `storage.py`
  - authoritative for persisted artifact schema, filenames, and directory layout
- `schemas.py`
  - authoritative for runtime contracts
- `report.py`
  - authoritative for report content and rendered report file creation
- `search.py`
  - authoritative for strategy-spec generation from parameter grids

## Contract migration plan

- Keep all workflow return types anchored to `schemas.py`.
- Make every path written into a workflow result originate from `storage.py` or `report.py`.
- Keep workflow metadata in `metadata` only when the field is protocol-scoped and not a reusable schema contract.
- Treat train/test split mechanics and fold generation as orchestration protocol, not data-loader or search semantics.

## Duplicate logic removal plan

- Remove any orchestration-local assumptions about ranked-results columns or output filenames if found during implementation.
- Remove any orchestration-local recomputation of report paths or artifact paths that can be derived from storage-owned helpers.
- Keep strategy-validity semantics authoritative in `search.py` and concrete strategy construction; any workflow-local guard must be explicitly documented as protocol-only.
- Keep analytics semantics authoritative in `metrics.py` and `benchmark.py`; orchestration may package values but not define them.

## Helper classification audit

- Pure orchestration
  - `run_experiment()`
  - `run_experiment_with_artifacts()`
  - `run_search()`
  - `run_validate_search()`
  - `run_walk_forward_search()`
  - `_split_market_data_by_ratio()`
  - `_validate_train_windows()`
  - `_generate_walk_forward_folds()`
  - These helpers primarily receive specs/config, decide workflow order, and choose which downstream owner to call next.

- Domain execution coordination
  - `_run_experiment_on_market_data()`
  - `_run_search_on_market_data()`
  - `build_strategy()`
  - `_build_validation_metadata()`
  - `ExperimentExecutionOutput`
  - These helpers coordinate multiple domain/runtime owners in one workflow step. The runner-local `ExperimentExecutionOutput` wrapper now keeps execution/output pairing explicit without promoting that bundle into a domain or persistence contract.

- Non-runner concern
  - `search_reporting.save_best_search_report()`
  - `search_reporting.save_search_comparison_report()`
  - `search_reporting.load_top_search_equity_curves()`
  - `search_reporting.build_search_curve_label()`
  - `walk_forward_aggregation.aggregate_walk_forward_test_metrics()`
  - `walk_forward_aggregation.aggregate_walk_forward_benchmark_metrics()`
  - `benchmark.normalize_benchmark_summary()`
  - These helpers now sit behind explicit non-runner owners because they encode report-input shaping, artifact loading, label formatting, aggregate-result semantics, or benchmark-summary transformation rather than pure sequencing.

## Current boundary hotspots

- Runner still owns workflow protocol helpers:
  - `_split_market_data_by_ratio()`
  - `_validate_train_windows()`
  - `_generate_walk_forward_folds()`
  - `_build_validation_metadata()`
  - These are currently treated as orchestration protocol helpers rather than separate reusable domain contracts. They are acceptable in runner as long as they do not start defining cross-module schema or artifact semantics.

- Runner still composes workflow-scoped path structure:
  - search workflow uses `search_root / "runs"` and `run_{index:03d}`
  - validation workflow uses `train_search`, `train_best`, and `test_selected`
  - walk-forward workflow uses `folds/fold_{index:03d}`
  - These names currently act as workflow sequencing/layout choices, not storage-owned file schema. If more modules start depending on them directly, they should be re-evaluated as a separate orchestration contract.

- Return-contract pressure is reduced but still worth monitoring:
  - `_run_experiment_on_market_data()` now returns `ExperimentExecutionOutput`.
  - This wrapper is intentionally runner-local. If similar bundles begin to cross into search, validation, or storage ownership, they should be split rather than generalized into a new shared contract.

## Verification plan

- Add or update tests proving:
  - persisted artifact names and layouts still come from storage-owned behavior,
  - orchestration returns schema-owned result objects,
  - search and validation workflows do not redefine search-space rules,
  - report workflow helpers do not define report content themselves,
  - runner can coordinate report generation through `ArtifactReceipt` and `ExperimentExecutionOutput` without treating runtime results as artifact locators.
- Review `experiment_runner.py` for any path strings, column lists, or schema dicts that duplicate storage or schema ownership.

## Temporary migration states

- Temporary state:
  - `build_strategy()` remains in `experiment_runner.py`
  - workflow protocol helpers remain in `experiment_runner.py`
- Stabilized state:
  - search-report preparation now lives in `search_reporting.py`
  - walk-forward aggregate policy now lives in `walk_forward_aggregation.py`
  - benchmark summary normalization now lives in `benchmark.py`
  - single-run execution coordination now uses runner-local `ExperimentExecutionOutput`
- Removal trigger:
  - only move remaining runner responsibilities if a future change introduces a clearer authoritative owner or if the helpers start encoding reusable semantics outside orchestration.
