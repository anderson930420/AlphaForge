# Design: formalize-report-view-model-contract

## Goal

- Make the report layer a clear consumer of upstream facts instead of a second analytics or orchestration layer.
- Keep `report.py` as the canonical owner of report view-model semantics while preserving the existing storage, execution, metrics, benchmark, and CLI ownership boundaries.

## Design summary

- Define the report view-model family in `report.py`.
- Treat `search_reporting.py` and `experiment_runner.py` as source-data gatherers that build or pass explicit report inputs, not as owners of report meaning.
- Keep `visualization.py` as a pure figure renderer that consumes chart-ready data and presentation-only validation rules.
- Keep `storage.py` as the authority for artifact refs and path layout, with report code only consuming those refs for presentation.

## Assembly shape

- The report contract should be a structured composite with:
  - domain facts,
  - presentation refs,
  - figure inputs,
  - display metadata.
- The composite should be mode-specific so single-run, search comparison, validation, and walk-forward surfaces can require different fields without inventing different ownership rules.

## Migration approach

- Preserve the current report rendering entry points.
- Route any ad hoc assembly in `experiment_runner.py` and `search_reporting.py` through report-owned helpers or report-owned dataclasses.
- Keep storage refs explicit and opaque during presentation link generation.
- Keep figure validation presentation-only and avoid moving chart preconditions into upstream business logic.

## Risks

- If report inputs remain spread across runner and search helpers, the contract can still drift even if the renderers look stable.
- If validation and walk-forward inputs are added without the same fact/presentation split, the boundary will be inconsistent across report modes.
- If figure-precondition constants are duplicated outside visualization, report code can again become a hidden owner of chart semantics.

