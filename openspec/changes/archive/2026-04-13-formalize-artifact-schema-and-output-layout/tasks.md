# Tasks

## 1. Spec and contract alignment

- [ ] 1.1 Update proposal and boundary specs to name `src/alphaforge/storage.py` as the canonical owner for persisted artifact schema and output layout.
- [ ] 1.2 Explicitly separate canonical storage facts from derived presentation refs in the persistence contract.
- [ ] 1.3 Identify every downstream consumer that must treat storage-owned paths as authoritative only.

## 2. Code migration

- [ ] 2.1 Move any remaining layout or filename authority out of `experiment_runner.py`, `report.py`, `search_reporting.py`, and `cli.py`.
- [ ] 2.2 Remove or downgrade duplicate path constants and layout assumptions outside `storage.py`.
- [ ] 2.3 Update runtime-facing outputs so storage receipts remain the source of canonical artifact paths.

## 3. Verification

- [ ] 3.1 Add or update tests that prove single-run, search, validation, and walk-forward layouts remain storage-owned.
- [ ] 3.2 Add or update tests that prove report links and CLI payloads consume derived refs instead of inventing path truth.
- [ ] 3.3 Add or update tests that prove runtime dataclasses and persisted schemas remain separate contracts.

## 4. Cleanup

- [ ] 4.1 Remove stale comments or docstrings that imply presentation or orchestration modules own output layout.
- [ ] 4.2 Update derived documentation and worklog references so readers can find the storage contract as the source of truth.
