# Tasks

## 1. Spec and contract alignment

- [x] 1.1 Finalize the search-report linking spec so `search_reporting.py` is the canonical owner of linking behavior and `report.py` is the canonical renderer.
- [x] 1.2 Explicitly document `SearchReportLinkContext.link_base_dir` as the relative-link base and `search_display_name` as a display-only label.
- [x] 1.3 Explicitly document `best_report_path` and `search_report_path` as optional presentation refs, not persistence truth.

## 2. Code migration

- [x] 2.1 Keep `search_reporting.py` as the only module that prepares search comparison report inputs and passes explicit link context to the renderer.
- [x] 2.2 Keep `report.py` limited to rendering links from explicit inputs, with no hidden `search_root` inference.
- [x] 2.3 Ensure `ArtifactReceipt` remains a persistence reference object that may carry optional presentation refs without becoming a presentation-domain object.
- [x] 2.4 Leave `cli.py` discovery behavior unchanged except for passing through the explicit presentation refs that search reporting already produces.

## 3. Verification

- [x] 3.1 Add or update focused report tests proving relative links are rendered from explicit link context only.
- [x] 3.2 Add or update search-report tests proving `best_report_path` is linked only when explicitly provided.
- [x] 3.3 Add or update contract-oriented tests proving `search_report_path` remains an optional presentation ref and not persistence truth.

## 4. Cleanup

- [x] 4.1 Remove any residual wording in docstrings or README text that implies `search_root` is hidden layout truth for search-link rendering.
- [x] 4.2 Update the worklog and archive notes after the implementation pass confirms the contract is stable.
