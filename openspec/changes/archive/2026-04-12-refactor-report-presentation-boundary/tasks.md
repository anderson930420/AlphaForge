# Tasks

## 1. Spec and contract alignment

- [x] 1.1 Create a change-local presentation boundary spec that assigns single canonical owners for report rendering, figure generation, and CLI output payload assembly.
- [x] 1.2 Inventory every report input, visualization input, and CLI output field that currently depends on implicit artifact/path/layout assumptions.
- [x] 1.3 Classify each presentation-facing contract as one of:
  - report-owned rendering contract,
  - visualization-owned figure contract,
  - CLI-owned output payload contract,
  - storage-owned artifact reference consumed by presentation.

## 2. Code migration

- [x] 2.1 Remove or isolate report-side layout/path inference that should instead consume explicit `ArtifactReceipt` or report input contracts.
- [x] 2.2 Make presentation-only validation in `visualization.py` explicit and keep it separate from runtime/persistence schema ownership.
- [x] 2.3 Align CLI output assembly so `cli.py` derives payload fields from canonical runtime and storage/report owners rather than reconstructing parallel output semantics.
- [x] 2.4 Add explicit helper boundaries or lightweight presentation input contracts only if needed to eliminate ambiguous ownership; do not introduce new modules unless the ambiguity cannot be resolved in place.

## 3. Verification

- [x] 3.1 Add or update tests proving report rendering uses canonical presentation inputs and does not redefine artifact schema or benchmark/metric semantics.
- [x] 3.2 Add or update tests proving visualization input requirements are presentation-only and do not create a second runtime/persistence schema authority.
- [x] 3.3 Add or update tests proving CLI output payloads match the chosen user-facing contract and remain derived from canonical owners.

## 4. Cleanup

- [x] 4.1 Update README and relevant docstrings so user-facing output descriptions match the canonical presentation boundary.
- [x] 4.2 Remove stale helper logic or comments that still imply runner, storage, or runtime models own presentation contracts.
