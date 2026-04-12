# Proposal: refactor-report-presentation-boundary

## Boundary problem

- `src/alphaforge/report.py`, `src/alphaforge/visualization.py`, and `src/alphaforge/cli.py` all participate in user-facing output, but the repository does not yet define one canonical presentation contract boundary.
- `report.py` currently assembles HTML, generates human-facing tables, and renders artifact links, which creates a risk that it will also start redefining artifact semantics or persistence layout assumptions.
- `visualization.py` currently validates figure input columns for presentation, but the boundary between presentation-only column requirements and runtime/persistence schema ownership is not explicitly specified.
- `cli.py` currently assembles JSON payloads that are already documented in `README.md`, but the repo does not yet state whether CLI output shape is part of the presentation layer or an independent downstream contract.
- The current implementation now also uses thin explicit presentation-input contracts (`ExperimentReportInput`, `SearchReportLinkContext`, `SearchExecutionOutput`), but those contracts need to be named and described in the OpenSpec artifacts so they do not drift back into implicit helper state.
- Without an explicit boundary, future changes can let HTML reports, CLI payloads, and figures drift from each other even when they are all describing the same experiment artifacts.

## Why

- The storage and runner boundaries are already fixed, so the next most likely ownership drift is in user-facing output contracts.
- If presentation ownership remains underspecified, `report.py` can silently start owning artifact semantics, `visualization.py` can silently start owning runtime schema, and `cli.py` can silently become a parallel report contract.
- The repo already promises user-visible outputs such as `best_report.html`, `search_report.html`, `report_path`, `search_report_path`, and ranked/search summaries, so those contracts need one canonical ownership model before the next feature adds more output forms.

## What Changes

- Define the presentation-layer boundary for:
  - report input contracts,
  - visualization input contracts,
  - CLI output payload ownership,
  - human-facing artifact link rendering,
  - presentation-only validation versus runtime/persistence validation.
- Make the new thin presentation contracts explicit in the change artifacts:
  - `ExperimentReportInput` for single-run report rendering inputs,
  - `SearchReportLinkContext` for search report link rendering,
  - `SearchExecutionOutput` for search workflow presentation outputs.
- Make `report.py` authoritative for report rendering contracts and report-level relative artifact link presentation.
- Make `visualization.py` authoritative for figure generation plus presentation-only chart input validation.
- Keep `storage.py` authoritative for artifact schema, filenames, and directory layout, while requiring presentation layers to consume explicit artifact references rather than infer layout.
- Keep `cli.py` authoritative for CLI JSON/text output assembly as a user-facing command contract derived from runtime and persistence owners.

## Canonical ownership decision

- `src/alphaforge/report.py` becomes the single canonical owner of rendered report content and report-level presentation contracts.
- `src/alphaforge/visualization.py` becomes the single canonical owner of figure-generation contracts and presentation-only input requirements needed to build those figures.
- `src/alphaforge/cli.py` remains the single canonical owner of CLI output payload assembly and command-facing output shape.
- `src/alphaforge/storage.py` remains the single canonical owner of artifact schema, filenames, and directory layout; presentation code must not redefine them.
- `src/alphaforge/schemas.py`, `src/alphaforge/benchmark.py`, `src/alphaforge/metrics.py`, and `src/alphaforge/experiment_runner.py` remain authoritative only for their existing runtime, semantic, and orchestration responsibilities.

## Scope

- Primary modules:
  - `src/alphaforge/report.py`
  - `src/alphaforge/visualization.py`
  - `src/alphaforge/cli.py`
- Direct boundary counterparts:
  - `src/alphaforge/storage.py`
  - `src/alphaforge/experiment_runner.py`
  - `src/alphaforge/schemas.py`
  - `src/alphaforge/benchmark.py`
- User-facing contracts and artifacts:
  - single-run HTML report generation
  - search comparison HTML report generation
  - report-level relative artifact links
  - CLI JSON payloads for `run`, `search`, `validate-search`, `walk-forward`, and `twse-search`
  - visualization input requirements for equity, drawdown, benchmark, and trade-marker figures

## Migration risk

- Search comparison reports can regress if report rendering continues to infer layout from search-root conventions instead of explicit artifact references.
- CLI output can diverge from HTML/report behavior if command payload fields are not explicitly classified as CLI-owned derived contracts.
- Visualization behavior can regress if figure input validation keeps depending on unstated persistence/runtime columns instead of explicit presentation contracts.
- README examples can become stale if documented output payloads and report expectations are not tied back to the new canonical presentation owners.

## Acceptance conditions

- `report.py` owns report rendering inputs, sections, human-facing tables, and relative link rendering without redefining artifact schema or metric semantics.
- `visualization.py` owns figure-building input requirements and plot-ready transformation without owning persistence schema, report composition, or CLI output shape.
- `cli.py` owns CLI payload assembly and must derive artifact references from `ArtifactReceipt` or storage-owned serializers rather than infer layout independently.
- No presentation module redefines storage-owned filenames, storage-owned artifact layout, runtime result schema, metric formulas, or benchmark semantics.
- Tests and README can point to one canonical owner for:
  - report content,
  - figure generation,
  - CLI output payloads,
  - presentation-level artifact links.
