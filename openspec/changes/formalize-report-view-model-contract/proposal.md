# Proposal: formalize-report-view-model-contract

## Boundary problem

- `src/alphaforge/report.py` renders report content, but `src/alphaforge/experiment_runner.py` currently assembles `ExperimentReportInput` directly and `src/alphaforge/search_reporting.py` assembles search comparison inputs and link context inline.
- `src/alphaforge/visualization.py` validates figure inputs, but there is no explicit report-view-model contract that says which fields are domain facts, which fields are presentation refs, and which module owns that distinction.
- Validation and walk-forward surfaces currently reuse orchestration bundles and storage refs without a dedicated report-input boundary, which makes report payloads easy to drift.

## Canonical ownership decision

- `src/alphaforge/report.py` becomes the canonical owner of report view-model assembly and report-render input semantics.
- `src/alphaforge/search_reporting.py` and `src/alphaforge/experiment_runner.py` remain upstream assemblers and adapters only.
- `src/alphaforge/visualization.py` remains the figure-rendering owner only.
- `src/alphaforge/storage.py` remains the canonical owner of persisted artifact paths and output layout only.

## Scope

- Report input dataclasses and helpers for single-run, search comparison, validation, and walk-forward presentation surfaces.
- The split between upstream domain facts and presentation-only refs such as report links and artifact receipts.
- The figure-input sub-contract handed to `visualization.py`.
- Report-facing assembly rules for search, validation, and walk-forward outputs.

## Migration risk

- If report inputs remain assembled ad hoc in orchestration code, report output can drift from one workflow to another.
- If presentation refs are treated as facts, report links can start substituting for authoritative runtime data.
- If figure input requirements remain implicit inside `visualization.py`, report code may continue to guess which fields are required for charts.

## Acceptance conditions

- Report renderers consume report-owned view-models rather than raw orchestration bundles or ad hoc dicts.
- Each report mode has an explicit input contract with a stable split between domain facts and presentation refs.
- `report.py` remains the only authority for report input field meaning.
- `visualization.py` remains downstream of already-assembled figure inputs and does not own the report-view-model contract.
