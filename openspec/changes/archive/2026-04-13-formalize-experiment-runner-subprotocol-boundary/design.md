# Design: formalize-experiment-runner-subprotocol-boundary

## Goal

- Keep `experiment_runner.py` as the orchestration boundary while making each internal workflow protocol explicit enough that the module can be refactored without blurring ownership.

## Design summary

- Treat the runner as a protocol coordinator, not a domain owner.
- Make single-run, search, validate-search, and walk-forward behavior separate subprotocols.
- Keep persistence and report triggering as sequencing steps only.
- Keep public runner bundles as receipts over authoritative owners, not as new truth layers.

## Assembly shape

- The runner should accept request DTOs and protocol parameters, sequence canonical owners, and aggregate the resulting facts into workflow bundles.
- Each subprotocol should be separately describable in terms of:
  - inputs,
  - called authoritative modules,
  - allowed outputs,
  - forbidden ownership.

## Migration approach

- Preserve current public entry points and result bundles.
- Make the protocol boundaries explicit in specs first, then keep the code aligned with those boundaries.
- Avoid moving any domain rules into the runner while tightening the orchestration seams.

## Risks

- If protocol receipts are not classified clearly, callers may start relying on runner bundles as if they were domain models.
- If persistence/report triggering is not treated as sequencing, the runner can start re-owning storage or report meaning.
- If walk-forward and validate-search are not named as distinct protocols, their reuse of search and scoring can look like an accidental duplication rather than intentional orchestration.

