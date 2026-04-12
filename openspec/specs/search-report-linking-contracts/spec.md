# search-report-linking-contracts Specification

## Purpose

- Define the canonical ownership boundary for search-related report linking.
- Make search comparison links, best-report links, and relative artifact links explicit rather than inferred from hidden workflow layout.
- Keep presentation-link behavior downstream of storage-owned artifact refs and CLI discovery output.

## Canonical owner

- `src/alphaforge/search_reporting.py` is the authoritative owner of search-report linking behavior and search-report presentation composition.
- `src/alphaforge/report.py` is the authoritative owner of report rendering and link markup generation from explicit presentation inputs.
- `src/alphaforge/storage.py` remains the authoritative owner of persisted artifact refs and directory layout.

## Allowed responsibilities

- `search_reporting.py` MAY:
  - prepare search comparison report inputs,
  - load top-ranked equity curves for presentation,
  - construct and pass an explicit `SearchReportLinkContext`,
  - pass explicit `best_report_path` and report-ref inputs into report rendering,
  - save rendered search report artifacts after rendering is complete.
- `report.py` MAY:
  - render relative links from explicit context and explicit artifact paths,
  - compose HTML tables and labels for comparison reports,
  - display link text for run artifacts and best-report references,
  - render report HTML without knowing workflow-specific layout beyond the provided link context.

## Explicit non-responsibilities

- `search_reporting.py` MUST NOT own runtime execution law, metric formulas, benchmark formulas, or persisted artifact schema.
- `report.py` MUST NOT infer search artifact relationships from `search_root` or any other hidden directory-layout assumption when an explicit link context exists.
- `report.py` MUST NOT redefine `best_report_path` or `search_report_path` as persistence truth.
- `storage.py` MUST NOT define search-report link markup or relative link rendering rules.

## Inputs / outputs / contracts

### Inputs

- `SearchReportLinkContext`
- `ArtifactReceipt` optional presentation refs
- `best_report_path` as an explicit presentation ref
- `search_report_path` as an explicit presentation ref
- ranked search results and artifact receipts passed from orchestration

### Outputs

- Search comparison HTML with relative run-artifact links rendered from an explicit base directory
- Best-report hyperlinks rendered only when the best result and best report are explicitly available
- Search report HTML saved under the report owner's chosen presentation path

### Contract rules

- `SearchReportLinkContext.link_base_dir` SHALL define the only relative-link base used by search comparison report helpers.
- `SearchReportLinkContext.search_display_name` SHALL define the human-facing title/display label only.
- `best_report_path` SHALL mean the optional best-run presentation HTML path that a search comparison report may link to.
- `search_report_path` SHALL mean the optional search comparison presentation HTML path produced by the search-reporting flow.
- `report.py` SHALL render relative paths from explicit artifact references and the supplied `link_base_dir`, not by reconstructing workflow layout from runtime objects.

## Invariants

- Search comparison report linking is presentation-only and downstream of storage-owned artifact refs.
- Relative links in search reports are stable only within the explicit `link_base_dir` contract.
- `best_report_path` and `search_report_path` remain presentation refs even when exposed through CLI or receipt objects.
- Search report linking must not become a second source of truth for persisted artifact naming.
- The same run artifact may be referenced in both CLI output and search comparison HTML, but both references must derive from the same explicit artifact ref.

## Cross-module dependencies

- `search_reporting.py` depends on:
  - `report.py` for HTML rendering
  - `storage.py` for persisted artifact refs
  - `benchmark.py` for benchmark summary preparation used in search report composition
- `report.py` depends on:
  - `SearchReportLinkContext`
  - explicit `ArtifactReceipt` refs
  - explicit `best_report_path` inputs
- `cli.py` depends on:
  - orchestration outputs that may include optional presentation refs
  - but it does not own linking behavior

## Failure modes if this boundary is violated

- Search comparison reports start linking to the wrong relative path because `report.py` re-infers layout from `search_root`.
- Best-report hyperlinks drift from the actual presentation artifact because path meaning was not explicitly bounded.
- Search report content and CLI discovery output become inconsistent about what a "report path" means.
- Downstream docs or tooling must reverse-engineer the report directory tree instead of relying on an explicit link contract.

## Migration notes from current implementation

- `search_reporting.py` already builds search comparison reports and passes `SearchReportLinkContext` into `report.py`.
- `report.py` already uses `link_base_dir` plus explicit artifact refs to render search links.
- The current implementation is treated as the starting point, but the contract is now stated explicitly so `search_root` is not read as hidden truth.

## Open questions / deferred decisions

- Whether future report types should reuse `SearchReportLinkContext` or introduce a narrower context object is deferred.
- Whether additional presentation refs beyond `best_report_path` and `search_report_path` should be added later is deferred.

## Scenarios

### Scenario: Search report links are rendered from explicit context

- GIVEN a search comparison report is rendered
- WHEN the report needs to link run artifacts and the best report
- THEN the renderer SHALL use `SearchReportLinkContext.link_base_dir` plus explicit artifact refs
- AND it SHALL NOT infer link targets from hidden `search_root` layout assumptions

### Scenario: Best report path is a presentation ref only

- GIVEN a search run produces a best-report HTML artifact
- WHEN that artifact path is surfaced to search reporting or CLI output
- THEN it SHALL be treated as an optional presentation ref
- AND it SHALL NOT redefine persisted experiment artifact ownership

### Scenario: Optional report refs remain optional in receipts

- GIVEN a search run does not generate report HTML
- WHEN its artifact receipt is materialized
- THEN the canonical persisted refs SHALL still be present
- AND optional presentation refs SHALL be allowed to remain empty

