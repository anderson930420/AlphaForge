# Delta for Report Presentation Boundary

## ADDED Requirements

### Requirement: search-comparison presentation derives parameter labels from the selected strategy parameters

`src/alphaforge/report.py` and `src/alphaforge/search_reporting.py` SHALL render search-comparison labels from the selected strategy parameters rather than hardcoding MA-only column names.

#### Purpose

- Allow the same report path to present MA crossover results and breakout results without creating a second report schema.
- Keep search-comparison presentation as a derived view over strategy parameters, not a family-specific hardcoded table.

#### Canonical owner

- `src/alphaforge/report.py` remains the canonical owner of rendered report content.
- `src/alphaforge/search_reporting.py` remains the helper owner that prepares report inputs and link context.

#### Allowed responsibilities

- `report.py` MAY render search-comparison table headers and row labels from the parameter keys present in each ranked result.
- `search_reporting.py` MAY build curve labels from strategy parameters in a family-aware but generic way.
- MA crossover may continue to display `Short Window` / `Long Window` labels when those parameter keys are present.
- Breakout may display `Lookback Window` labels or an equivalent title-cased label derived from `lookback_window`.

#### Explicit non-responsibilities

- `report.py` and `search_reporting.py` MUST NOT hardcode MA-only parameter labels as the only supported presentation.
- `report.py` MUST NOT invent new family-specific semantics just to render breakout results.

#### Inputs / outputs / contracts

- Inputs:
  - ranked `ExperimentResult` values
  - explicit artifact receipts
  - strategy parameter mappings from `StrategySpec.parameters`
- Output:
  - report table headers and comparison labels derived from the provided parameters

#### Invariants

- The same strategy parameters should render the same family-aware labels across repeated runs.
- Presentation remains derived from authoritative runtime and storage owners.

#### Scenario: breakout search results render without MA-only labels

- GIVEN a ranked search report contains breakout results
- WHEN `report.py` renders the comparison table and top-curve labels
- THEN the report SHALL derive labels from the breakout parameter names
- AND it SHALL NOT require `short_window` or `long_window` to be present
