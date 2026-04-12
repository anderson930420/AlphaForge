# Proposal: refactor-experiment-runner-boundary

## Boundary problem

- `src/alphaforge/experiment_runner.py` currently owns multiple workflow jobs in one file: single-run orchestration, search orchestration, validation orchestration, walk-forward orchestration, report workflow orchestration, and strategy dispatch.
- The file also assembles workflow metadata, reads persisted artifacts back for reporting, and applies protocol guards such as train-window sufficiency checks.
- Without an explicit change boundary, future refactors can accidentally move persisted schema logic, analytics formulas, report naming, or search-space rules into `experiment_runner.py`, turning it into a god module.

## Why

- The highest current architecture risk in AlphaForge is not missing functionality; it is ownership drift inside orchestration code.
- If orchestration remains underspecified, future changes will duplicate rules already owned by storage, schemas, reporting, analytics, or search.
- Defining this boundary first reduces the chance that subsequent refactors will fix one overlap by creating another.

## Canonical ownership decision

- `src/alphaforge/experiment_runner.py` remains the single canonical owner of runtime workflow orchestration semantics.
- `src/alphaforge/storage.py` remains the single canonical owner of persisted artifact schemas, file naming, and directory layout.
- `src/alphaforge/schemas.py` remains the single canonical owner of in-memory result contracts.
- `src/alphaforge/report.py` remains the single canonical owner of rendered report content.
- `src/alphaforge/backtest.py`, `src/alphaforge/metrics.py`, `src/alphaforge/benchmark.py`, and `src/alphaforge/search.py` remain the single canonical owners of their respective domain rules.
- `experiment_runner.py` must lose any implicit ownership over:
  - persisted artifact schema details,
  - output directory naming rules,
  - analytics formulas,
  - benchmark formulas,
  - search-space generation semantics,
  - presentation structure.

## Scope

- Affected runtime module:
  - `src/alphaforge/experiment_runner.py`
- Direct boundary counterparts:
  - `src/alphaforge/storage.py`
  - `src/alphaforge/schemas.py`
  - `src/alphaforge/report.py`
  - `src/alphaforge/search.py`
  - `src/alphaforge/backtest.py`
  - `src/alphaforge/metrics.py`
  - `src/alphaforge/benchmark.py`
- Affected specs and artifacts:
  - change-local orchestration boundary spec
  - architecture boundary map alignment
  - code changes that reduce implicit ownership inside `experiment_runner.py`
  - tests proving orchestration-only behavior

## Migration risk

- Search output behavior can regress if `experiment_runner.py` currently relies on storage details that are not yet made explicit.
- Validation and walk-forward outputs can drift if workflow-local metadata and persisted artifact fields are not clearly separated.
- Search report generation can break if report orchestration and report rendering ownership are disentangled incorrectly.
- Strategy dispatch can become inconsistent if refactoring changes where unsupported strategy names are rejected.

## Acceptance conditions

- `experiment_runner.py` contains only workflow orchestration decisions, protocol segmentation rules, strategy dispatch, and workflow-scoped metadata assembly.
- No persisted artifact schema, filename, or directory-layout rule is redefined in `experiment_runner.py`.
- No metric or benchmark formula is redefined in `experiment_runner.py`.
- Workflow tests can point to one canonical owner for:
  - orchestration sequencing,
  - persistence schema,
  - runtime result schemas,
  - report content,
  - search-space generation.
