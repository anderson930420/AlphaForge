# Design: normalize-persistence-artifact-contracts

## Canonical ownership mapping

- `src/alphaforge/storage.py`
  - owns persisted experiment artifact contracts
  - owns filename and directory layout conventions
  - owns receipt materialization
- `src/alphaforge/report.py`
  - owns HTML report rendering only
- `src/alphaforge/search_reporting.py`
  - owns search-report presentation wiring only
- `src/alphaforge/experiment_runner.py`
  - consumes storage contracts and remains orchestration-only
- `src/alphaforge/runner_workflows.py`
  - remains the orchestration implementation owner and does not own persistence semantics

## Contract migration plan

- Keep the runtime contract layer unchanged.
- Keep runner orchestration unchanged.
- Make the persisted experiment output set explicit in storage docstrings/spec text:
  - single-run artifacts
  - ranked search artifacts
  - validation artifacts
  - walk-forward artifacts
- Keep `ArtifactReceipt` as a storage-owned reference object that points at persisted experiment outputs plus optional presentation refs.
- Keep report HTML outputs outside the canonical persisted experiment artifact set while allowing them to be referenced optionally by receipts or orchestration outputs.

## Duplicate logic removal plan

- Do not duplicate the canonical persisted file set in multiple modules.
- Remove any ambiguity in storage docstrings or comments that might imply report HTML is part of the canonical experiment persistence layer.
- Normalize the path semantics so the same concept is described the same way in storage, CLI, and report-adjacent code.
- Keep any existing persisted file naming behavior unless a contract term needs to be made explicit.

## Verification plan

- Add or tighten tests that assert:
  - single-run persisted files exist and have the expected names
  - ranked search produces the canonical ranked-results CSV
  - validation produces the canonical validation summary and train-ranked-results files
  - walk-forward produces the canonical summary and fold-results files
  - report HTML files are present only when presentation/report flows generate them
  - receipts expose persisted artifact refs and optional report refs separately
- Prefer tests that assert contract shape and file presence, not incidental implementation internals.

## Temporary migration states

- No major temporary duplication is expected.
- If a storage docstring or helper name still suggests that HTML report outputs are canonical experiment artifacts, that wording should be corrected as part of the same change rather than left in a transitional state.
- If any path reference is still ambiguous, it should be clarified in the storage contract text instead of creating a new abstraction layer.

