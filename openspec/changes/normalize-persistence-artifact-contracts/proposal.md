# Proposal: normalize-persistence-artifact-contracts

## Boundary problem

- `src/alphaforge/storage.py` writes persisted JSON/CSV artifacts, but the exact persisted output set is still clearer in implementation than in approved contract text.
- `ArtifactReceipt` already exists, but its relationship to canonical persisted experiment artifacts versus optional presentation/report artifacts is not yet sharply frozen.
- Search, validation, and walk-forward workflows persist nested artifacts with slightly different layouts, and the contract for which paths are canonical versus convenience references is still easy to misread.
- Report HTML outputs are intentionally not canonical runtime artifacts, but the current persistence layer and report layer still sit close enough that the distinction needs to be documented explicitly.

## Canonical ownership decision

- `src/alphaforge/storage.py` becomes the single authoritative owner of canonical persisted experiment artifact contracts, artifact receipts, filename conventions, and directory layout for persisted experiment outputs.
- `src/alphaforge/report.py` and `src/alphaforge/search_reporting.py` remain presentation owners for HTML report artifacts only.
- `src/alphaforge/experiment_runner.py` and the workflow modules remain orchestration-only consumers of storage-owned persistence contracts.
- `ArtifactReceipt` remains a storage-owned receipt contract and must not become a business-domain object.

## Scope

- Single experiment persisted outputs:
  - `experiment_config.json`
  - `metrics_summary.json`
  - `trade_log.csv`
  - `equity_curve.csv`
  - `ArtifactReceipt`
- Ranked search persisted outputs:
  - `ranked_results.csv`
  - per-run artifacts under the search root
  - optional presentation/report artifacts returned as explicit receipt fields
- Validation persisted outputs:
  - `validation_summary.json`
  - `train_ranked_results.csv`
  - nested train/test experiment artifacts
- Walk-forward persisted outputs:
  - `walk_forward_summary.json`
  - `fold_results.csv`
  - nested fold experiment artifacts
- Presentation artifacts that must stay separate from canonical persisted experiment artifacts:
  - `report.html`
  - `best_report.html`
  - `search_report.html`

## Migration risk

- Any ambiguity in persisted path semantics can break downstream tooling or tests that read output paths directly.
- If report artifacts are not clearly separated from canonical persisted experiment artifacts, storage may start owning HTML concerns indirectly.
- Tightening persistence contracts may require updates to tests that currently assert paths by implementation detail rather than by explicit contract.
- Because the runtime and runner boundaries are already frozen, this change must avoid touching execution semantics or orchestration ownership.

## Acceptance conditions

- Persisted artifact boundaries are explicitly documented.
- `storage.py` ownership is clearly persistence-only.
- Required persisted outputs for single, search, validation, and walk-forward flows are explicit.
- Receipt/path semantics are explicit and non-overlapping.
- Report artifacts are clearly separated from canonical persisted experiment artifacts.
- Runtime contracts remain unchanged.
- Runner orchestration boundaries remain unchanged.
- Persistence tests lock the intended file/path/schema behavior.
- The resulting structure makes future downstream tooling and reporting safer.

## Follow-up changes

- `report-presentation-boundary` remains the owner of report rendering semantics; this change only clarifies how persisted experiment artifacts differ from report outputs.

