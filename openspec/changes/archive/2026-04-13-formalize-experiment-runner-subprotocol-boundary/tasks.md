# Tasks

## 1. Define the runner subprotocols in `src/alphaforge/experiment_runner.py`

- Make the single-run, search-execution, validate-search, walk-forward, and persistence/report-triggering subprotocols explicit in the contract.

## 2. Preserve canonical ownership boundaries

- Keep search, scoring, execution, storage, and reporting semantics outside the runner.
- Keep runner bundles as protocol receipts only.

## 3. Distinguish workflow sequencing from business truth

- Ensure the runner contract clearly states which outputs are upstream facts, which are workflow refs, and which are protocol receipts.

## 4. Sync docs or specs if needed

- Update any docs or index entries that still imply the runner owns workflow semantics rather than protocol orchestration.

## 5. Validate the boundary

- Add or update focused tests if needed to prove the protocol bundles and workflow reuse remain aligned with the new contract.

