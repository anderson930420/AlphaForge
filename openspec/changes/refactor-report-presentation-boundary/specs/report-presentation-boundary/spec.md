# Delta for Report Presentation Boundary

## ADDED Requirements

### Requirement: Presentation contracts have explicit rendering owners

User-facing presentation contracts in AlphaForge SHALL be owned explicitly by `src/alphaforge/report.py`, `src/alphaforge/visualization.py`, and `src/alphaforge/cli.py` according to their distinct rendering roles, and SHALL NOT be redefined by storage, runtime schemas, or orchestration modules.

#### Purpose

- Define one canonical presentation boundary so reports, figures, and CLI output describe the same experiment artifacts without each layer inventing its own parallel contract.
- Prevent `report.py`, `visualization.py`, and `cli.py` from silently absorbing storage-owned artifact semantics, runtime-owned schema meaning, or orchestration-owned workflow logic.

#### Canonical owner

- `src/alphaforge/report.py` is the single authoritative owner of report rendering contracts and report-level human-facing link presentation.
- `src/alphaforge/visualization.py` is the single authoritative owner of figure-generation contracts and presentation-only figure input validation.
- `src/alphaforge/cli.py` is the single authoritative owner of CLI output payload assembly and command-facing user output shape.
- `src/alphaforge/storage.py` remains the single authoritative owner of artifact references, filenames, and directory layout consumed by presentation.

#### Allowed responsibilities

- `report.py` MAY:
  - assemble HTML, markdown, or text report content,
  - define report sections, tables, headings, and human-facing labels,
  - render relative or display-oriented artifact links from explicit artifact references,
  - persist rendered report files if the saved file is the rendered report artifact itself.
- `visualization.py` MAY:
  - validate figure inputs only to the extent required for chart construction,
  - derive plot-ready series or markers from already-computed data,
  - build figures for single-run and comparison reports.
- `cli.py` MAY:
  - choose which derived fields appear in a command payload,
  - serialize runtime results and storage-owned artifact refs into command-facing JSON/text output,
  - include report paths returned by report owners.

#### Explicit non-responsibilities

- `report.py` MUST NOT:
  - define storage-owned artifact schema,
  - define filenames or output directory layout for non-report artifacts,
  - recompute metric formulas, score formulas, or benchmark semantics,
  - infer persistence layout from runtime result objects when explicit artifact refs exist.
- `visualization.py` MUST NOT:
  - define report page composition,
  - define CLI payload fields,
  - define persistence schema or artifact layout,
  - become the authoritative owner of runtime data schema.
- `cli.py` MUST NOT:
  - define report content,
  - define figure input semantics,
  - redefine artifact naming or directory layout,
  - recompute benchmark or metric semantics for user output.

#### Inputs / outputs / contracts

- Report input contract:
  - `ExperimentResult` and other runtime result objects for already-computed domain truth
  - storage-owned `ArtifactReceipt` for persisted artifact references
  - normalized benchmark summaries from `benchmark.py`
  - ranked search results and comparison curve payloads prepared without guessing persistence layout
- Visualization input contract:
  - `EquityCurveFrame` inputs for equity and drawdown figures
  - trade-log frames for price/trade figures
  - label-to-equity-curve mappings for comparison figures
  - visualization-required columns are presentation-only contracts and MUST be documented there, not in storage or runtime schemas unless they are truly shared runtime truth
- CLI output contract:
  - command-facing payloads are derived from `schemas.py`, `storage.py`, and `report.py`
  - artifact refs in CLI output MUST come from storage-owned serializers or explicit report-returned paths
  - CLI output MAY omit internal runtime fields that are not part of the user-facing command contract

#### Invariants

- Presentation modules consume explicit runtime results and artifact references; they do not become parallel authorities for artifact schema or runtime semantics.
- Relative artifact links shown in reports are presentation-layer renderings only and MUST NOT redefine storage-owned layout semantics.
- Visualization validation is authoritative only for chart-building preconditions, not for canonical market-data or persistence schemas.
- CLI output payloads are authoritative only as command-facing derived contracts and MUST remain downstream of runtime, storage, and report owners.
- If the same path appears in a report and CLI payload, both presentations MUST derive it from the same storage-owned or report-owned source.

#### Cross-module dependencies

- `report.py` depends on:
  - runtime results from `schemas.py`
  - artifact refs from `storage.py`
  - normalized benchmark summaries from `benchmark.py`
  - figures from `visualization.py`
- `visualization.py` depends on:
  - already-computed frames from execution/storage/report callers
  - no ownership over persistence naming or runtime result schema beyond presentation-only input validation
- `cli.py` depends on:
  - orchestration outputs from `experiment_runner.py`
  - runtime serializers and storage-owned serializers
  - report-returned paths for generated reports

#### Failure modes if this boundary is violated

- HTML reports and CLI payloads drift because each layer constructs artifact paths differently.
- Figures break for some workflows because visualization quietly depends on columns that no authoritative contract guarantees.
- Report rendering disagrees with storage outputs because report code guesses directory layout rather than consuming explicit artifact refs.
- CLI payloads become a second report contract because `cli.py` starts inventing user-facing summaries independently of report/storage/runtime owners.
- Later presentation refactors require changes in storage or runner because presentation assumptions were never isolated.

#### Migration notes from current implementation

- `report.py` currently renders relative artifact paths using `search_root` plus `ArtifactReceipt`.
- `visualization.py` currently owns `REPORT_EQUITY_CURVE_REQUIRED_COLUMNS`; this is acceptable only if those columns remain presentation-only requirements.
- `cli.py` currently constructs search report paths with helper functions and assembles compact summary payloads documented in `README.md`.
- `README.md` currently documents report artifacts and CLI summary payloads; those descriptions must remain derived from canonical presentation owners rather than becoming a parallel source of truth.

#### Open questions / deferred decisions

- Whether CLI output payloads should remain inside this presentation boundary or later be split into a dedicated CLI-output spec if command contracts become materially more complex than report/figure contracts.
- Whether report link rendering should continue using `search_root` as a presentation context input or move to a narrower report-input helper once the presentation contract is implemented.
- Whether comparison-report input shaping should remain in `search_reporting.py` or migrate into a report-adjacent contract if more presentation workflows appear.

#### Scenario: Reports render artifact links from explicit references

- GIVEN a ranked search report needs to show artifact locations for each run
- WHEN `report.py` renders the comparison table
- THEN it SHALL consume `ArtifactReceipt` or explicit report input paths
- AND it SHALL NOT infer artifact filenames from runtime result schema or invent storage layout rules locally

#### Scenario: Visualization input validation remains presentation-only

- GIVEN a figure builder in `visualization.py` requires `datetime`, `equity`, or `close`
- WHEN validation runs before chart construction
- THEN that validation SHALL be treated as a presentation precondition only
- AND it SHALL NOT become the authoritative owner of persisted CSV schema or canonical runtime result schema

#### Scenario: CLI output remains downstream of runtime and storage owners

- GIVEN a CLI command returns JSON describing results and artifact locations
- WHEN `cli.py` assembles the payload
- THEN runtime result fields SHALL come from canonical runtime serializers
- AND artifact paths SHALL come from storage-owned serializers or report-returned paths
- AND `cli.py` SHALL NOT invent a parallel artifact or report contract
