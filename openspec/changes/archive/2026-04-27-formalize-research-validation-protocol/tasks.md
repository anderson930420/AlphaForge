# Tasks

## 1. Specification artifacts

- [x] 1.1 Create `proposal.md` describing the research-process boundary and ownership exclusions.
- [x] 1.2 Create `design.md` describing protocol phases, cross-boundary dependencies, and deferred implementation.
- [x] 1.3 Create a `research-validation-protocol` spec delta with clear MUST / SHOULD requirements.

## 2. Acceptance criteria coverage

- [x] 2.1 Specify development/holdout separation and frozen final holdout requirements.
- [x] 2.2 Specify development-only strategy search, parameter search, scoring-rule selection, risk-filter selection, walk-forward validation, and permutation diagnostics.
- [x] 2.3 Specify that walk-forward validation must produce multiple development-period out-of-sample folds.
- [x] 2.4 Specify block permutation / block shuffle preference and diagnostic-only interpretation.
- [x] 2.5 Specify the pre-holdout freeze set and one-time final holdout evaluation rule.
- [x] 2.6 Specify final report disclosure requirements.

## 3. Validation

- [x] 3.1 Run `openspec validate formalize-research-validation-protocol --type change --no-interactive`.
- [x] 3.2 Confirm no new strategy logic, backtest semantics, storage layout, CLI formatting, or report-rendering implementation details were introduced.
- [x] 3.3 Log the completed specification step through the local Obsidian workflow.
