# Delta for Persistence Artifact Contracts

## ADDED Requirements

### Requirement: `storage.py` is the canonical owner of persisted experiment artifact contracts

`src/alphaforge/storage.py` SHALL own canonical persisted experiment artifact contracts, filename conventions, directory layout, and artifact-receipt materialization, while runtime behavior remains owned by the frozen runtime modules.

#### Purpose

- Freeze the persisted output contract so storage behavior is stable and explicit.
- Prevent persisted file shape from drifting independently of runtime contracts.
- Make it clear which outputs are canonical persisted experiment artifacts and which outputs are presentation artifacts.

#### Canonical owner

- `src/alphaforge/storage.py` is the single authoritative owner of persisted experiment artifact contracts.
- `src/alphaforge.report.py` and `src/alphaforge.search_reporting.py` remain the authoritative owners of report HTML artifacts only.
- `ArtifactReceipt` is storage-owned.

#### Allowed responsibilities

- Define canonical persisted filenames and directory layout for experiment outputs.
- Serialize runtime objects into persisted JSON and CSV payloads.
- Materialize `ArtifactReceipt` instances that reference persisted experiment artifacts.
- Return persistence outputs from save functions without redefining runtime meaning.
- Serialize optional presentation artifact references when those references are already produced by report/presentation flows.

#### Explicit non-responsibilities

- `storage.py` MUST NOT own runtime execution law, metric formulas, benchmark formulas, or report rendering.
- `storage.py` MUST NOT become the owner of HTML report content.
- `storage.py` MUST NOT turn receipts into business-domain objects.
- `storage.py` MUST NOT infer new runtime truth from persisted files.

#### Inputs / outputs / contracts

- Inputs:
  - runtime dataclasses from `schemas.py`
  - runtime frames and trade logs produced by `backtest.py`
  - explicit report paths returned by report/presentation flows
- Canonical persisted outputs:
  - `experiment_config.json`
  - `metrics_summary.json`
  - `trade_log.csv`
  - `equity_curve.csv`
  - `ranked_results.csv`
  - `validation_summary.json`
  - `train_ranked_results.csv`
  - `walk_forward_summary.json`
  - `fold_results.csv`
- Presentation artifact outputs that are explicitly non-canonical persisted experiment artifacts:
  - `best_report.html`
  - `search_report.html`
  - `report.html`
- Artifact receipt contract:
  - `run_dir`
  - `equity_curve_path`
  - `trade_log_path`
  - `metrics_summary_path`
  - optional `best_report_path`
  - optional `comparison_report_path`

#### Invariants

- Persisted artifact contracts are layered below runtime contracts and are not the same contract as the runtime dataclasses.
- Canonical experiment artifact paths are explicit and stable enough for downstream tooling to rely on.
- Optional presentation/report path fields in receipts do not make the receipt a business-domain object.
- Report HTML files are convenience/presentation artifacts, not canonical persisted experiment artifacts.

#### Cross-module dependencies

- `experiment_runner.py` and workflow modules consume storage-owned save functions and receipts.
- `cli.py` may serialize artifact receipts for user-facing output but does not own the persisted artifact contract.
- `report.py` and `search_reporting.py` may return report paths, but those paths remain presentation artifacts rather than canonical experiment artifacts.

#### Failure modes if this boundary is violated

- A report HTML file is mistaken for the canonical persisted experiment artifact.
- Downstream tooling reads implementation-specific path behavior that later changes without contract review.
- Validation and walk-forward summaries drift from ranked-result and per-fold outputs because there is no single persistence contract.
- Receipts accumulate domain logic and stop being a simple persistence reference object.

#### Migration notes from current implementation

- `ArtifactReceipt` already carries canonical experiment artifact refs plus optional report refs.
- `save_single_experiment()`, `save_validation_result()`, and `save_walk_forward_result()` already materialize persisted experiment artifacts.
- `save_ranked_results_with_columns()` and `save_ranked_results_artifact()` already write search-ranked CSVs.
- `save_experiment_report()` remains presentation-layer file export and should stay outside the canonical persisted experiment artifact set.

#### Open questions / deferred decisions

- Whether a separate typed manifest for persisted artifact receipts is needed later is deferred.
- Whether report HTML paths should eventually be stored in a narrower presentation receipt is deferred.

#### Scenario: single-run persisted outputs are explicit and stable

- GIVEN a caller saves a single experiment run
- WHEN `storage.py` persists the run
- THEN the canonical persisted experiment artifacts SHALL include `experiment_config.json`, `metrics_summary.json`, `trade_log.csv`, and `equity_curve.csv`
- AND the returned `ArtifactReceipt` SHALL point at those files explicitly

### Requirement: ranked search persistence has a canonical CSV contract and nested run layout

`src/alphaforge/storage.py` SHALL define the canonical persisted contract for ranked search outputs, including the ranked-results CSV shape and the nested per-run artifact layout.

#### Purpose

- Make search persistence predictable for CLI consumers and downstream tooling.
- Ensure ranked results and per-run artifacts are stored under an explicit, stable layout.

#### Canonical owner

- `src/alphaforge/storage.py` is the canonical owner of ranked search persistence contracts.
- `src/alphaforge.search_reporting.py` may produce presentation artifacts for search results, but it does not own the ranked-results persistence contract.

#### Allowed responsibilities

- Write `ranked_results.csv` with a stable canonical column contract.
- Materialize per-run experiment artifacts under the search root.
- Preserve optional report artifact paths when generated by report/presentation flows.

#### Explicit non-responsibilities

- `storage.py` MUST NOT decide ranking semantics or score formulas.
- `storage.py` MUST NOT decide report HTML content or report link semantics.
- `storage.py` MUST NOT infer rank-order from persisted artifact paths.

#### Inputs / outputs / contracts

- Inputs:
  - ranked `ExperimentResult` objects
  - optional parameter column hints
  - optional search-root output directories
- Canonical ranked-results CSV contract:
  - `strategy`
  - parameter columns derived from the search grid
  - `total_return`
  - `annualized_return`
  - `sharpe_ratio`
  - `max_drawdown`
  - `win_rate`
  - `turnover`
  - `trade_count`
  - `score`
- Layout contract:
  - search-root ranked results are stored at `ranked_results.csv`
  - per-run artifacts live under the search root in run-specific subdirectories
- Optional presentation refs:
  - `best_report_path`
  - `comparison_report_path`

#### Invariants

- The ranked-results CSV is a persisted artifact contract, not a runtime schema.
- Parameter columns are part of the search persistence contract, but they are derived from the search grid rather than from runtime semantics.
- Optional presentation refs stay optional and do not change the canonical search CSV contract.

#### Cross-module dependencies

- `experiment_runner.py` consumes search persistence outputs via storage helpers.
- `cli.py` may surface `ranked_results_path` to users.
- `report.py` and `search_reporting.py` may create presentation artifacts alongside ranked search persistence.

#### Failure modes if this boundary is violated

- Search CSV column order or naming drifts without a contract update.
- CLI or downstream tooling starts depending on implementation-specific path trees rather than the canonical search layout.
- Presentation artifact paths become indistinguishable from canonical ranked-search persistence.

#### Migration notes from current implementation

- The ranked-results CSV currently already has a stable set of metric and score columns.
- Search run artifacts already live under a search root with per-run directories.
- This change freezes those details as explicit persistence contract language rather than changing the data layout.

#### Open questions / deferred decisions

- Whether additional search export formats beyond CSV should ever be canonical is deferred.

#### Scenario: search persistence exposes a stable ranked-results contract

- GIVEN a search run is saved to disk
- WHEN storage writes the ranked-results artifact
- THEN the CSV SHALL include the canonical metric and score columns in a stable layout
- AND the search root SHALL contain per-run persisted experiment artifacts

### Requirement: validation persistence has a canonical summary contract

`src/alphaforge/storage.py` SHALL define the canonical persisted contract for validation outputs, including validation summary shape and train-ranked-results references.

#### Purpose

- Keep validation summary persistence explicit and stable.
- Separate validation summary persistence from the nested experiment outputs it references.

#### Canonical owner

- `src/alphaforge/storage.py` is the canonical owner of validation persistence contracts.

#### Allowed responsibilities

- Write `validation_summary.json` as the canonical validation summary artifact.
- Persist `train_ranked_results.csv` when validation outputs include ranked training results.
- Preserve nested train-best and test-selected experiment artifacts under validation-specific subdirectories.

#### Explicit non-responsibilities

- `storage.py` MUST NOT redefine validation split semantics or train/test selection rules.
- `storage.py` MUST NOT turn validation persistence into a second runtime contract.
- `storage.py` MUST NOT own validation report presentation.

#### Inputs / outputs / contracts

- Inputs:
  - `ValidationResult`
  - optional `train_ranked_results_path`
  - nested train/test experiment outputs
- Canonical validation summary JSON contract:
  - `data_spec`
  - `split_config`
  - `selected_strategy_spec`
  - `train_best_result`
  - `test_result`
  - `test_benchmark_summary`
  - `train_ranked_results_path`
  - `metadata`
- The validation summary file path is canonical as a persisted summary artifact.

#### Invariants

- Validation summary persistence is separate from the nested experiment artifacts it references.
- The validation summary JSON is a persisted contract, not a runtime result object.
- `train_ranked_results_path` is a stable persisted reference when validation wrote ranked training outputs.

#### Cross-module dependencies

- `experiment_runner.py` constructs the runtime validation result and delegates persistence.
- `cli.py` serializes the validation result for user-facing output.
- `report.py` does not own validation persistence.

#### Failure modes if this boundary is violated

- Validation summary files and nested experiment artifacts become inconsistent.
- Consumers treat the validation summary JSON as if it were the runtime validation object itself.
- The path to `train_ranked_results.csv` becomes ambiguous or disappears from user-facing persistence contracts.

#### Migration notes from current implementation

- Validation persistence already writes a summary JSON and optionally ranked training results.
- This change freezes that arrangement and clarifies the status of `train_ranked_results_path`.

#### Open questions / deferred decisions

- Whether validation should later persist an explicit artifact manifest is deferred.

#### Scenario: validation persistence preserves summary and ranked-train outputs

- GIVEN a validation run is saved
- WHEN storage writes validation artifacts
- THEN the canonical validation summary SHALL be written to `validation_summary.json`
- AND `train_ranked_results.csv` SHALL remain a stable validation-side persisted artifact when present

### Requirement: walk-forward persistence has a canonical summary and fold-results contract

`src/alphaforge/storage.py` SHALL define the canonical persisted contract for walk-forward outputs, including the summary JSON, fold-results CSV, and nested fold experiment artifacts.

#### Purpose

- Freeze the shape of walk-forward persistence so fold summaries remain stable.
- Make it clear which walk-forward files are canonical persisted outputs versus nested experiment artifacts.

#### Canonical owner

- `src/alphaforge/storage.py` is the canonical owner of walk-forward persistence contracts.

#### Allowed responsibilities

- Write `walk_forward_summary.json` as the canonical summary artifact.
- Write `fold_results.csv` as the canonical fold-results artifact.
- Materialize nested fold experiment artifacts under fold-specific directories.
- Include fold path references in fold-results CSV rows when those references are derived from storage layout.

#### Explicit non-responsibilities

- `storage.py` MUST NOT own walk-forward fold generation or train/test protocol semantics.
- `storage.py` MUST NOT own walk-forward aggregation formulas.
- `storage.py` MUST NOT own report rendering for walk-forward outputs.

#### Inputs / outputs / contracts

- Inputs:
  - `WalkForwardResult`
  - nested fold `WalkForwardFoldResult` objects
  - output directory for the walk-forward run
- Canonical walk-forward summary JSON contract:
  - `data_spec`
  - `walk_forward_config`
  - `folds`
  - `aggregate_test_metrics`
  - `aggregate_benchmark_metrics`
  - `walk_forward_summary_path`
  - `fold_results_path`
  - `metadata`
- Canonical fold-results CSV contract:
  - fold index and date boundaries
  - selected strategy parameters
  - train and test result summary columns
  - benchmark summary columns
  - fold path reference when storage materializes it

#### Invariants

- Walk-forward summary and fold-results persistence are separate canonical outputs.
- Fold artifacts remain nested per fold and are not collapsed into a single undifferentiated output directory.
- The fold path reference in CSV output is a storage-derived persisted reference, not a runtime domain field.

#### Cross-module dependencies

- `experiment_runner.py` constructs the runtime walk-forward result and delegates persistence.
- `cli.py` serializes walk-forward results for user-facing output.
- `report.py` does not own walk-forward persistence.

#### Failure modes if this boundary is violated

- Fold-level and aggregate-level outputs drift because the persisted summary and CSV are not treated as separate canonical outputs.
- The fold path reference becomes ambiguous between runtime truth and storage layout.
- Downstream tooling has no stable file contract for walk-forward runs.

#### Migration notes from current implementation

- Walk-forward persistence already writes a summary JSON and fold-results CSV.
- The fold-results CSV already includes a fold path reference derived from storage layout; this change makes that semantic explicit rather than accidental.

#### Open questions / deferred decisions

- Whether fold path references should later move into a dedicated receipt field rather than the fold-results CSV is deferred.

#### Scenario: walk-forward persistence preserves summary and fold-result outputs

- GIVEN a walk-forward run is saved
- WHEN storage writes walk-forward artifacts
- THEN the canonical summary SHALL be written to `walk_forward_summary.json`
- AND the fold results SHALL be written to `fold_results.csv`
- AND nested fold experiment artifacts SHALL remain stored per fold directory

### Requirement: presentation HTML artifacts remain separate from canonical persisted experiment artifacts

`src/alphaforge/report.py` and `src/alphaforge/search_reporting.py` SHALL continue to own HTML presentation artifacts, and those files SHALL remain separate from canonical persisted experiment artifacts written by `storage.py`.

#### Purpose

- Prevent report outputs from being mistaken for canonical persisted experiment state.
- Keep presentation artifact naming and semantics explicit.

#### Canonical owner

- `src/alphaforge.report.py` and `src/alphaforge.search_reporting.py` are the canonical owners of report HTML artifacts.
- `src/alphaforge.storage.py` is not the owner of report HTML content.

#### Allowed responsibilities

- Render `report.html`, `best_report.html`, and `search_report.html`.
- Return explicit report paths through presentation contracts and receipts.
- Consume storage-owned artifact receipts for rendering, but not redefine canonical persisted artifact contracts.

#### Explicit non-responsibilities

- Report HTML artifacts MUST NOT be treated as canonical persisted experiment artifacts.
- Presentation modules MUST NOT redefine storage-owned JSON/CSV schemas.
- Storage MUST NOT absorb HTML report content ownership.

#### Inputs / outputs / contracts

- Inputs:
  - explicit report input contracts
  - explicit artifact receipts
  - ranked results and comparison inputs
- Outputs:
  - `report.html`
  - `best_report.html`
  - `search_report.html`
- These outputs are presentation artifacts and are deliberately separate from canonical persisted experiment artifacts.

#### Invariants

- Report HTML paths are optional presentation refs, not runtime truth.
- Report artifacts do not replace canonical persisted experiment outputs.
- Search and single-run reporting may reference persisted artifacts, but those references do not alter the storage contract.

#### Cross-module dependencies

- `experiment_runner.py` and `cli.py` may ask for report generation.
- `storage.py` may carry optional report refs inside receipts, but does not own the report HTML content.

#### Failure modes if this boundary is violated

- HTML report paths are treated as if they were canonical experiment outputs.
- Storage and report ownership become indistinguishable, making future persistence changes risky.
- CLI or downstream tooling starts relying on presentation artifacts as stable runtime data.

#### Migration notes from current implementation

- Report HTML artifacts are already generated through report/search-report flows rather than storage save functions.
- `ArtifactReceipt` already carries optional report refs, which should remain optional and presentation-scoped.

#### Open questions / deferred decisions

- Whether a future manifest should enumerate presentation artifacts separately from persisted experiment artifacts is deferred.

#### Scenario: report HTML files remain presentation artifacts only

- GIVEN a report or search report is generated
- WHEN the HTML file is written
- THEN it SHALL remain a presentation artifact
- AND it SHALL NOT be promoted to the canonical persisted experiment artifact set

