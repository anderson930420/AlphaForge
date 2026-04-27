# Design: add-development-holdout-split-workflow

## Canonical ownership mapping

- `runner_protocols.py`
  - owns date-range validation and split mechanics for development/holdout frames used by runner workflows.
  - does not own market-data normalization, backtest semantics, search semantics, or persistence schemas.
- `runner_workflows.py`
  - owns the research validation protocol sequence.
  - calls existing development-period search, walk-forward, optional permutation, and final holdout single-run evaluation helpers.
- `experiment_runner.py`
  - exposes public facade functions and execution-output bundles for callers.
- `schemas.py`
  - may define passive dataclasses for request/period/summary/plan data.
  - remains passive and does not import registry, storage, CLI, or runner modules.
- `storage.py`
  - owns `research_protocol_summary.json`, serialization, and any protocol artifact receipt.
- `cli.py`
  - parses `research-validate` arguments and delegates to `experiment_runner.py`.

## Runtime flow

1. CLI or caller constructs a research validation request with data spec, strategy family, parameter grid, development period, holdout period, walk-forward config, optional permutation config, and backtest config.
2. Workflow loads canonical OHLCV data through `load_market_data`.
3. Runner split helper returns development and holdout frames using inclusive datetime ranges.
4. Split helper rejects:
   - missing datetime column,
   - overlapping date ranges,
   - holdout start at or before development end,
   - empty development period,
   - empty holdout period,
   - intersecting development/holdout datetimes.
5. Workflow runs development search on development data only and selects the best ranked candidate.
6. Workflow runs walk-forward validation on development data only, labeling the output as development-period OOS evidence.
7. Workflow optionally runs existing permutation diagnostics on development data only for the frozen selected candidate.
8. Workflow freezes a protocol plan before holdout evaluation, including strategy family, selected parameters, selection rule, scoring formula name, transaction cost assumptions, periods, search breadth, walk-forward config, and permutation config.
9. Workflow evaluates the final holdout once by running the frozen strategy spec on holdout data only.
10. Workflow builds and optionally persists a protocol summary.

## Persisted artifact contract

- The top-level research protocol workflow writes `research_protocol_summary.json` under `output_dir / experiment_name`.
- The summary payload must include:
  - development and holdout period boundaries,
  - development and holdout row counts,
  - selected strategy and selected parameters,
  - selection rule and scoring formula name,
  - search-space size and tried combination counts,
  - tried strategy family count,
  - walk-forward configuration and summary,
  - optional permutation configuration and summary,
  - frozen plan,
  - final holdout metrics,
  - transaction cost assumptions,
  - artifact references for nested development evidence when produced.

## Boundary exclusions

- Do not modify `backtest.py`.
- Do not redefine canonical OHLCV schema or market-data acceptance.
- Do not move strategy construction or signal generation ownership.
- Do not make strategy families responsible for final holdout protection.
- Do not add report-rendering logic to the workflow.
- Do not put persisted artifact layout or JSON payload ownership in CLI code.
- Do not make schemas import registry, runners, CLI, or storage.

## Verification plan

- Add focused unit tests for split validation.
- Add workflow tests with patched sub-workflows to prove development-only data and frozen holdout candidate behavior.
- Add storage tests for the protocol summary artifact and serializer.
- Add CLI help and small end-to-end smoke tests.
- Run `openspec validate add-development-holdout-split-workflow --type change --no-interactive`.
- Run `python -m pytest`.

## Deferred decisions

- Full protocol enforcement receipts or global one-time holdout locks are deferred.
- Report rendering that presents the protocol summary as a human-readable final report is deferred.
- Multi-strategy protocol-level family search is deferred; this change supports one explicit strategy family selected by the request.
- New permutation null engines are deferred; the workflow may call the existing block permutation diagnostic only when enabled.
