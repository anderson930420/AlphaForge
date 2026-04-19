# Tasks

## 1. Spec and contract alignment

- [x] 1.1 Update proposal and boundary specs to name `storage.py` as the canonical owner of persisted experiment artifact contracts.
- [x] 1.2 Explicitly separate canonical persisted experiment artifacts from presentation/report HTML artifacts.
- [x] 1.3 Identify which receipt fields are canonical persisted refs and which are optional presentation refs.

## 2. Code migration

- [x] 2.1 Update storage-facing docstrings/comments to make canonical persisted output sets explicit.
- [x] 2.2 Clarify any ambiguous artifact naming or path semantics in `storage.py`, `report.py`, and `search_reporting.py` without changing runtime or runner ownership.
- [x] 2.3 Keep report HTML generation outside storage ownership while preserving existing path behavior.

## 3. Verification

- [x] 3.1 Add or update tests that assert the canonical persisted file set for single-run, search, validation, and walk-forward flows.
- [x] 3.2 Add or update tests that distinguish canonical persisted artifacts from presentation/report HTML artifacts.
- [x] 3.3 Add or update tests that prove artifact receipts expose persisted refs and optional report refs separately.

## 4. Cleanup

- [x] 4.1 Remove stale wording or comments that blur the boundary between storage artifacts and report artifacts.
- [x] 4.2 Update local worklog and Obsidian notes for the persistence contract normalization milestone.
