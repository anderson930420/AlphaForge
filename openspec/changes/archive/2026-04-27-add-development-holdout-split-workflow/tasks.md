# Tasks

## 1. OpenSpec artifacts

- [x] 1.1 Create proposal, design, and task artifacts for `add-development-holdout-split-workflow`.
- [x] 1.2 Add a `research-validation-protocol` spec delta for the runtime split/frozen-holdout workflow.
- [x] 1.3 Add an artifact-schema/output-layout spec delta for `research_protocol_summary.json`.
- [x] 1.4 Run OpenSpec validation before runtime implementation.

## 2. Runtime contracts and split helper

- [x] 2.1 Add passive runtime dataclasses for research periods, frozen plan, protocol summary/config, and execution output as needed.
- [x] 2.2 Add a pure development/holdout split helper with validation for non-empty, disjoint, chronological date ranges.
- [x] 2.3 Add focused tests for valid split, overlapping ranges, empty development, and empty holdout.

## 3. Workflow orchestration

- [x] 3.1 Add a research validation protocol workflow that loads canonical data and splits development/holdout periods.
- [x] 3.2 Run development-period search on development data only and freeze the selected candidate/plan.
- [x] 3.3 Run development-period walk-forward validation on development data only and label it as development-period OOS evidence.
- [x] 3.4 Optionally run existing permutation diagnostics on development data only when enabled.
- [x] 3.5 Run final holdout evaluation once using only the frozen selected candidate on holdout data.
- [x] 3.6 Expose the workflow through the public runner facade.

## 4. Storage and CLI

- [x] 4.1 Add storage-owned protocol summary filename, serializer, receipt, and save function.
- [x] 4.2 Add `research-validate` CLI request assembly and JSON response output.
- [x] 4.3 Keep CLI free of orchestration, scoring, persistence schema, and report-rendering ownership.

## 5. Tests and verification

- [x] 5.1 Add workflow tests proving holdout rows are not passed into development search or walk-forward.
- [x] 5.2 Add workflow tests proving final holdout uses the frozen selected candidate and does not affect parameter selection.
- [x] 5.3 Add storage tests for `research_protocol_summary.json`.
- [x] 5.4 Add CLI help and tiny synthetic CLI smoke tests.
- [x] 5.5 Run `openspec validate add-development-holdout-split-workflow --type change --no-interactive`.
- [x] 5.6 Run `python -m pytest`.
- [x] 5.7 Log implementation and verification steps through the local Obsidian workflow.
