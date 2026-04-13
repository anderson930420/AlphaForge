# Tasks

## 1. Define the report-view-model family in `src/alphaforge/report.py`

- Add or refine the mode-specific report input contracts so single-run, search comparison, validation, and walk-forward surfaces all follow the same fact/presentation split.
- Keep the canonical ownership and validation rules in `report.py`.

## 2. Route orchestration through report-owned inputs

- Update `experiment_runner.py` and `search_reporting.py` so they gather upstream facts and pass structured report inputs instead of inventing ad hoc payload shapes.
- Keep those modules as adapters only.

## 3. Keep visualization downstream of report-ready figure inputs

- Ensure `visualization.py` only receives chart-ready inputs that were already shaped by the report contract.
- Keep figure validation presentation-only.

## 4. Verify the contract boundaries

- Add or update focused tests that prove report links remain presentation refs, report renderers do not recompute upstream facts, and mode-specific report inputs reject missing required data.

## 5. Update documentation if required by the new contract

- Sync any repo docs or spec indexes that still imply report input ownership is split across runner, search reporting, and visualization.

