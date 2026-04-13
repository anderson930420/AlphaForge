# Proposal: formalize-experiment-runner-subprotocol-boundary

## Boundary problem

- `src/alphaforge/experiment_runner.py` currently orchestrates single-run, search, validation, walk-forward, persistence, and report-triggering behavior in one place.
- Even with the execution, search, scoring, storage, report, and CLI boundaries already formalized, the runner’s internal protocol seams are still broad enough to hide ownership drift.
- The runner needs an explicit subprotocol contract so orchestration stays powerful without becoming a second owner of search, scoring, persistence, or report truth.

## Canonical ownership decision

- `src/alphaforge/experiment_runner.py` becomes the canonical owner of workflow protocol orchestration only.
- The runner’s subprotocols are explicitly owned as protocol flow:
  - single-run protocol,
  - search-execution protocol,
  - validate-search protocol,
  - walk-forward protocol,
  - persistence/report-triggering protocol when the workflow chooses to persist or render.
- `src/alphaforge/search.py`, `src/alphaforge.scoring.py`, `src/alphaforge.backtest.py`, `src/alphaforge.data_loader.py`, `src/alphaforge.storage.py`, and `src/alphaforge.report.py` remain the authoritative owners of their own domain semantics.

## Scope

- Runner orchestration across already-defined request contracts and authoritative lower-layer owners.
- Internal decomposition of single-run, search, validation, and walk-forward workflows.
- The distinction between protocol receipts/aggregates and domain truth.
- The relationship between runner sequencing and downstream persistence/report/view-model owners.

## Migration risk

- If the runner’s subprotocols remain implicit, it can keep accumulating workflow-specific truth that belongs elsewhere.
- If validation and walk-forward continue to share unlabelled runner logic, their protocol differences become hard to audit.
- If persistence and report triggering are not classified as sequencing only, runner outputs can start looking like parallel storage or report schemas.

## Acceptance conditions

- The runner’s internal protocol seams are explicit and separately named.
- Each subprotocol states which authoritative owners it calls and what it may aggregate.
- Runner outputs are clearly receipts or workflow aggregates, not new domain truth.
- The runner remains orchestration-only even when it sequences persistence and report triggering.
