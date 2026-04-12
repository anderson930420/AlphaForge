# Proposal: formalize-search-report-linking-contracts

## Boundary problem

- Search report generation is already functional, but the ownership of presentation-layer linking is still inferred from implementation flow instead of being frozen as an explicit contract.
- `src/alphaforge/search_reporting.py` currently constructs search comparison reports, loads top-ranked equity curves, and passes a `SearchReportLinkContext` into `report.py`.
- `src/alphaforge/report.py` currently renders human-facing links by combining a `link_base_dir` with `ArtifactReceipt.run_dir` and `best_report_path`, but the contract for those relative links is still only implicit in helper code.
- `ArtifactReceipt` carries optional presentation refs, but their role in search-report linking is not yet stated as a formal boundary in the spec.
- `best_report_path` and `search_report_path` are surfaced as presentation refs, yet downstream readers still need to infer whether they are canonical presentation outputs, optional conveniences, or persistence truth.

## Canonical ownership decision

- `src/alphaforge/search_reporting.py` becomes the canonical owner of search-report linking behavior.
- `src/alphaforge/report.py` remains the canonical owner of HTML rendering only and must not infer workflow layout or artifact relationships beyond explicit link inputs.
- `SearchReportLinkContext` becomes the explicit report-linking input contract for search comparison reports.
- `ArtifactReceipt.best_report_path` and `ArtifactReceipt.comparison_report_path` remain optional presentation refs only; they do not become runtime or persistence truth.
- `src/alphaforge/storage.py` keeps ownership of persisted artifact references and must not gain responsibility for presentation-link semantics.
- `src/alphaforge/cli.py` keeps ownership of CLI-facing discovery output and must not define presentation-link behavior.

## Scope

- `src/alphaforge/search_reporting.py`
- `src/alphaforge/report.py`
- `src/alphaforge/storage.py`
- `src/alphaforge/experiment_runner.py`
- `src/alphaforge/cli.py`
- `tests/test_report.py`
- `tests/test_runner.py`
- `tests/test_cli.py`

## Migration risk

- Search comparison HTML may change if any relative-link helper was relying on implicit `search_root` assumptions rather than explicit link context.
- `best_report_path` and `search_report_path` may need wording clarifications in docstrings, tests, or README notes so they are read as presentation refs, not persistence truth.
- CLI-visible discovery behavior should remain stable, but tests may need to be updated if the presentation-link contract becomes more explicit in output wording or helper return types.
- Backward compatibility risk is limited to report-link rendering and documentation wording; runtime results, persistence files, and CLI discovery keys are not intended to change.

## Acceptance conditions

- `search_reporting.py` is the explicit owner of search-report linking behavior.
- `report.py` renders links only from explicit link inputs and does not infer hidden layout truth from `search_root`.
- `SearchReportLinkContext` is documented as a report-local presentation contract with a clear base directory and display-name meaning.
- `best_report_path` and `search_report_path` are explicitly documented as optional presentation refs, not runtime or persistence truth.
- Search comparison report tests prove relative links are rendered from explicit context.
- Search report behavior remains compatible except for any clarified presentation wording required by the new contract.
