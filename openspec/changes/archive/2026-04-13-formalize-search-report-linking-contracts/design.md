# Design: formalize-search-report-linking-contracts

## Canonical ownership mapping

- `src/alphaforge/search_reporting.py`
  - Canonical owner of search-report linking behavior.
  - Owns preparation of search comparison report inputs, including explicit `SearchReportLinkContext`, ranked-result loading for comparison charts, and optional presentation refs passed into the report layer.
  - Continues to save rendered search report artifacts, but only after report rendering has consumed explicit link inputs.
- `src/alphaforge/report.py`
  - Canonical owner of report rendering and HTML link markup generation.
  - Renders search comparison links only from `SearchReportLinkContext` and explicit artifact/report paths.
  - Must not infer workflow layout from `search_root` or any other hidden path convention.
- `src/alphaforge/storage.py`
  - Canonical owner of persisted artifact refs and directory layout.
  - Continues to define `ArtifactReceipt` and persisted experiment artifact paths.
  - Does not own any report-linking semantics.
- `src/alphaforge/cli.py`
  - Owns CLI discovery output only.
  - Passes through optional presentation refs but does not derive or re-render link behavior.

## Contract migration plan

- Keep the current `SearchReportLinkContext` type as the explicit presentation-link boundary.
- Treat `link_base_dir` as the only stable relative-path base for search comparison report rendering.
- Treat `search_display_name` as a human-facing label only.
- Keep `best_report_path` and `search_report_path` as optional presentation refs in the report-linking flow and in `ArtifactReceipt`.
- Preserve the current `search_reporting.py -> report.py` call pattern, but make the contract explicit in the spec and tests so no caller can read `search_root` as hidden layout truth.
- If future report types need different relative-link rules, they should introduce their own context object rather than widening this one.

## Duplicate logic removal plan

- Remove any temptation for `report.py` to reconstruct artifact relationships from `search_root` or directory names.
- Keep `_build_relative_artifact_path()` and `_build_best_report_link()` as presentation helpers only, with explicit inputs and no hidden layout inference.
- Ensure `search_reporting.py` remains the only module that decides when a best report or comparison report is generated for search workflows.
- Do not duplicate search-report path semantics in CLI, storage, or runner modules.

## Verification plan

- Add or tighten tests in `tests/test_report.py` that prove:
  - search comparison links render correctly from explicit `SearchReportLinkContext`,
  - relative artifact links are derived from the supplied `link_base_dir`,
  - `best_report_path` is linked only when explicitly provided,
  - report rendering no longer depends on hidden `search_root` layout inference.
- Add or tighten tests in `tests/test_runner.py` or `tests/test_cli.py` only if they are needed to prove optional presentation refs still flow through unchanged.
- Run focused regression against report/search-report paths and compile checks for touched modules.

## Temporary migration states

- `search_root` may still be the value passed into `SearchReportLinkContext.link_base_dir`, but only as an explicit context value, not as hidden layout truth.
- During implementation, helper names may remain the same while the contract becomes explicit; they must be treated as rendering helpers, not layout authorities.
- No temporary duplication of search-report link ownership should remain after the refactor; the removal trigger is when report tests prove the renderer only depends on explicit link context and explicit artifact/report paths.

