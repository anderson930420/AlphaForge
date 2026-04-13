# Proposal: formalize-artifact-schema-and-output-layout

## Boundary problem

- Persisted artifact schema, filename conventions, and output layout are currently known by more than one module.
- `storage.py` owns most write-time persistence behavior, but `experiment_runner.py`, `report.py`, `cli.py`, and `search_reporting.py` also know enough about paths and filenames to reconstruct layout independently.
- Runtime dataclasses still carry or serialize persistence-facing fields, which makes it easier for persistence shape to drift into runtime truth.

## Canonical ownership decision

- `src/alphaforge/storage.py` becomes the single authoritative owner of persisted artifact schema, artifact naming, and output directory layout.
- `src/alphaforge/experiment_runner.py` may request persistence and consume returned references, but it must not own path layout or filename rules.
- `src/alphaforge/report.py` and `src/alphaforge/search_reporting.py` may render and persist reports, but they must not own canonical artifact layout.
- `src/alphaforge/cli.py` may display or forward derived paths, but it must not hardcode storage truth.
- `src/alphaforge/schemas.py` remains the runtime contract owner only.

## Scope

- Affected contracts:
  - persisted experiment artifacts
  - search artifact layouts
  - validation artifact layouts
  - walk-forward artifact layouts
  - report file placement
  - artifact receipts and derived path references
  - runtime-vs-persistence serialization boundaries
- Affected modules:
  - `src/alphaforge/storage.py`
  - `src/alphaforge/schemas.py`
  - `src/alphaforge/experiment_runner.py`
  - `src/alphaforge/report.py`
  - `src/alphaforge/search_reporting.py`
  - `src/alphaforge/cli.py`
  - `src/alphaforge/visualization.py`
  - documentation and tests that currently restate output paths

## Migration risk

- If filename conventions remain split across modules, CLI output, report links, and persisted files can drift from one another.
- If runtime dataclasses continue to act like persistence owners, code may start depending on fields that only exist because something was already saved.
- If report modules keep reconstructing file paths, link rendering can break when output roots change.
- If validation and walk-forward outputs keep their layout knowledge in orchestration, later workflow changes will require coordinated edits in multiple modules.

## Acceptance conditions

- The spec states one authoritative storage owner for persisted artifact schema and output layout.
- The spec states the canonical file sets for single-run, search, validation, and walk-forward persistence.
- The spec distinguishes canonical storage facts from derived presentation references.
- The spec states what runtime dataclasses may serialize and what they must not own.
- The spec states which modules may consume paths and which modules must not reconstruct them.
