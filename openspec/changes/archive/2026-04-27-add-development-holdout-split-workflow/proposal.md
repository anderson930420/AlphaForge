# Proposal: add-development-holdout-split-workflow

## Boundary problem

- The archived `research-validation-protocol` defines development/final-holdout separation, frozen plan evaluation, and non-tuning rules, but AlphaForge does not yet have a runtime workflow that enforces those rules at the data boundary.
- Existing `search`, `validate-search`, `walk-forward`, and `permutation-test` workflows can be run directly against any loaded data. They do not coordinate an explicit development-period split followed by a final holdout evaluation using a frozen candidate selected from development evidence only.
- Persisting a protocol-level summary would introduce a new artifact. That artifact must be storage-owned rather than assembled as an ad hoc CLI or runner JSON shape.

## Canonical ownership decision

- `src/alphaforge/runner_protocols.py` becomes the canonical owner of reusable development/holdout date-range split validation for runner workflows.
- `src/alphaforge/runner_workflows.py` becomes the canonical owner of sequencing the minimal research validation protocol workflow.
- `src/alphaforge/experiment_runner.py` exposes the public facade for the workflow without owning orchestration semantics.
- `src/alphaforge/cli.py` remains a request assembly boundary for the `research-validate` command.
- `src/alphaforge/storage.py` becomes the canonical owner of the persisted protocol summary artifact name and payload.
- Strategy families, `backtest.py`, market-data schema code, report rendering, and storage layout consumers do not own holdout protection or frozen-plan selection.

## Scope

- Add passive runtime dataclasses for research periods, frozen protocol plan, protocol summary, and workflow request if needed.
- Add a pure split helper that loads/receives canonical OHLCV data and returns disjoint development and holdout frames by datetime range.
- Add a `research-validate` workflow that:
  - loads canonical market data through the existing loader,
  - splits development and final holdout periods,
  - runs development-only search,
  - runs development-only walk-forward validation,
  - optionally runs development-only permutation diagnostics,
  - freezes the selected candidate/plan before final holdout,
  - evaluates final holdout once using the frozen candidate,
  - persists a protocol summary artifact.
- Add CLI support for `alphaforge research-validate`.
- Add storage-owned serialization and receipt support for `research_protocol_summary.json`.
- Add focused tests for split validation, development-only workflow calls, frozen holdout evaluation, CLI help, CLI smoke behavior, and storage persistence.

## Migration risk

- CLI behavior risk is limited to adding a new subcommand; existing commands should remain unchanged.
- Persisted artifact risk is controlled by adding an explicit storage spec delta and storage-owned filename/serializer rather than changing existing artifact schemas.
- Runtime behavior risk is concentrated in sequencing existing search, walk-forward, permutation, and single-run execution on explicitly split data. Existing backtest execution semantics and strategy signal generation must remain unchanged.
- Report behavior risk is low because this change does not implement report rendering or report layout changes.
- Compatibility risk is low for existing callers because the new workflow is additive and existing public runner functions remain unchanged.

## Acceptance conditions

- OpenSpec proposal, design, tasks, research-validation-protocol delta, and artifact-schema/output-layout delta exist.
- `openspec validate add-development-holdout-split-workflow --type change --no-interactive` passes before implementation.
- The workflow validates non-empty, disjoint, chronological development and holdout periods.
- Development search, walk-forward validation, and optional permutation diagnostics receive development-period data only.
- Final holdout evaluation receives holdout-period data only and uses the frozen selected candidate.
- Final holdout metrics do not alter selected parameters, selection rule, scoring formula, filters, acceptance criteria, or candidate promotion decisions.
- `research_protocol_summary.json` is storage-owned and clearly separates development evidence, walk-forward OOS evidence, optional permutation diagnostic evidence, frozen plan, and final holdout result.
- `python -m pytest` passes.
