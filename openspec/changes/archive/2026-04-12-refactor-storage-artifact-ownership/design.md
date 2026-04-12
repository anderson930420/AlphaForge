# Design: refactor-storage-artifact-ownership

## Canonical ownership mapping

- `schemas.py`
  - authoritative only for in-memory runtime contracts
  - not authoritative for JSON payloads, CSV column layouts, artifact paths, or output directories
- `storage.py`
  - authoritative for persisted artifact schemas
  - authoritative for JSON and CSV serialization shapes
  - authoritative for output path materialization
  - authoritative for artifact naming and directory layout
- `experiment_runner.py`
  - continues to orchestrate when persistence is invoked
  - does not own persisted artifact shape
- `report.py`
  - continues to own report rendering and report file content
  - storage ownership applies only if report persistence needs file-level layout rules

## Contract migration plan

- Separate runtime result contracts from persisted artifact contracts.
- Treat runtime dataclasses as source inputs to serialization, not as the persisted schema itself.
- Classify every persistence-facing field before removing it:
  - domain result
  - persisted artifact reference
  - storage residue
- Introduce storage-owned serializers or artifact-schema helpers for:
  - experiment configuration JSON
  - metrics summary JSON
  - ranked results CSV
  - validation summary JSON
  - walk-forward summary JSON
  - fold results CSV
- Keep runtime contract conversion explicit at the persistence boundary:
  - runtime object in
  - storage-owned artifact payload out
  - file path materialization out

## Current field classification

- Domain result:
  - `ExperimentResult.data_spec`
  - `ExperimentResult.strategy_spec`
  - `ExperimentResult.backtest_config`
  - `ExperimentResult.metrics`
  - `ExperimentResult.score`
  - `ValidationResult.split_config`
  - `ValidationResult.selected_strategy_spec`
  - `ValidationResult.train_best_result`
  - `ValidationResult.test_result`
  - `ValidationResult.test_benchmark_summary`
  - `WalkForwardFoldResult.fold_index`
  - `WalkForwardFoldResult.train_start`
  - `WalkForwardFoldResult.train_end`
  - `WalkForwardFoldResult.test_start`
  - `WalkForwardFoldResult.test_end`
  - `WalkForwardFoldResult.selected_strategy_spec`
  - `WalkForwardFoldResult.train_best_result`
  - `WalkForwardFoldResult.test_result`
  - `WalkForwardFoldResult.test_benchmark_summary`
  - `WalkForwardResult.walk_forward_config`
  - `WalkForwardResult.folds`
  - `WalkForwardResult.aggregate_test_metrics`
  - `WalkForwardResult.aggregate_benchmark_metrics`
- Persisted artifact reference:
  - `ExperimentResult.equity_curve_path`
  - `ExperimentResult.trade_log_path`
  - `ExperimentResult.metrics_path`
  - `ValidationResult.validation_summary_path`
  - `ValidationResult.train_ranked_results_path`
  - `WalkForwardResult.walk_forward_summary_path`
  - `WalkForwardResult.fold_results_path`
- Storage residue:
  - `WalkForwardFoldResult.fold_path`

## Classification-driven migration order

- First:
  - keep domain result fields unchanged
  - keep persisted artifact reference fields only as temporary migration outputs
  - stop treating storage residue as runtime truth
- Second:
  - move all serialization logic and path decisions into storage-owned helpers
- Third:
  - remove storage residue fields from runtime dataclasses
- Fourth:
  - decide whether persisted artifact reference fields remain on runtime results or move into separate storage receipts
  - during transition, mark deprecated runtime path fields explicitly and direct new callers to the storage-owned receipt

## Duplicate logic removal plan

- Remove `to_dict()` ownership of persistence-specific paths from runtime contracts where those paths are not required as in-memory domain truth.
- Remove any storage function behavior that reconstructs a new runtime dataclass merely to attach write-time file paths, unless a future spec explicitly defines those paths as runtime-visible contract fields.
- Remove any CLI or orchestration assumptions about artifact shape that are not derived from storage-owned serializers.
- Remove any caller dependence on `fold_path` as though it were domain result truth; treat it as the first storage-residue removal candidate.

## Verification plan

- Add tests that prove runtime result dataclasses can exist without persisted file paths.
- Add tests that prove storage-owned serializers define persisted JSON/CSV fields independently of runtime dataclass field order.
- Add tests that prove artifact naming and directory layout originate from storage-owned behavior only.
- Add tests that compare persisted artifact compatibility expectations when schema fields are added, removed, or renamed.
- Add tests or audits that prove storage residue fields are not required by CLI payload shape or persisted summary payloads before removing them.

## Temporary migration states

- Temporary state:
  - runtime dataclasses may still carry some persistence-facing path fields during refactor if removing them in one step would break too many callers
- Temporary interpretation:
  - persisted artifact reference fields are tolerated migration outputs
  - storage residue fields are tolerated only until direct callers are identified and replaced
- Receipt-first migration rule:
  - new callers MUST consume `ArtifactReceipt` rather than reading deprecated runtime path fields
  - report and comparison workflows MUST use receipt-owned artifact refs instead of inferring layout from `ExperimentResult`
- Removal trigger:
  - once storage-owned serialization helpers and caller integrations are in place, persistence-only path fields should be removed or narrowed to explicitly justified runtime-visible fields
