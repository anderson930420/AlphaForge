# Design: formalize-artifact-schema-and-output-layout

## Canonical ownership mapping

- `src/alphaforge/storage.py`
  - Own persisted artifact schemas, filenames, directory trees, receipts, and canonical path derivation.
- `src/alphaforge/schemas.py`
  - Own in-memory runtime contracts only.
- `src/alphaforge/experiment_runner.py`
  - Request persistence and consume receipts or presentation refs returned by storage-aligned helpers.
- `src/alphaforge/report.py`
  - Render report content and consume explicit artifact refs, but do not define layout rules.
- `src/alphaforge/search_reporting.py`
  - Render search presentation artifacts using storage-owned refs and path bases.
- `src/alphaforge/cli.py`
  - Display derived artifact refs and dispatch workflows without hardcoding canonical layout.
- `src/alphaforge/visualization.py`
  - Remain presentation-only and avoid artifact naming/layout decisions.

## Contract migration plan

- Keep `storage.py` as the only module that should define canonical filenames and tree layout for persisted outputs.
- Keep runtime result dataclasses separate from persisted schema definitions.
- Preserve the current top-level workflow roots for single-run, search, validation, and walk-forward outputs, but make their semantics explicit in storage rather than spread across callers.
- Treat report HTML file placement as a storage-owned path contract even though the report module writes the HTML bytes.
- Treat CLI report-path fields and search-report-link refs as derived references only.

## Duplicate logic removal plan

- Remove or downgrade any filename constants in presentation modules that duplicate storage-owned names.
- Remove or downgrade any path assembly in `experiment_runner.py` that reconstructs storage layout instead of consuming storage-owned outputs.
- Remove or downgrade any report-link helper logic that assumes layout truth instead of using explicit storage refs.
- Remove or downgrade any documentation or comments that describe `report.py`, `search_reporting.py`, or `cli.py` as owning artifact path conventions.
- Remove or downgrade any runtime-path fields that act like storage truth instead of persistence references.

## Verification plan

- Add or update tests that prove:
  - single-run, search, validation, and walk-forward outputs land in the canonical directory trees,
  - storage-owned filenames are stable and discoverable through receipts or returned paths,
  - report links are rendered from explicit refs and an explicit base directory,
  - CLI payloads display derived refs but do not redefine path truth,
  - runtime objects and persisted schemas are still separate contracts.

## Temporary migration states

- If existing presentation modules still carry local filename constants, treat them as temporary adapters only until storage-owned helpers replace them.
- If report HTML remains written by report/search-report modules, the path they write to must still be a storage-owned path contract.
- If runtime result objects still carry persistence-facing references during a transition, those fields must be classified as persistence references and not as runtime truth.
