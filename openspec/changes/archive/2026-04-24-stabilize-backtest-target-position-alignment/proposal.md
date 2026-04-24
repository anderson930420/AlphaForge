# Proposal: stabilize-backtest-target-position-alignment

## Boundary problem

- `run_backtest()` is a public execution boundary that consumes market data and target positions.
- It currently assigns `target_positions` directly into a copied market-data frame, allowing pandas index-label alignment to occur implicitly.
- A same-length `pd.Series` with stale or mismatched labels can therefore shift target positions or introduce missing values before the backtest fills/clips them, changing trades without an explicit error.

## Canonical ownership decision

- `src/alphaforge/backtest.py` is the canonical owner of target-position alignment, length validation, normalization, one-bar lag, turnover, cost, trade extraction, and equity construction.
- Strategy modules may produce target positions but must not define backtest input alignment behavior.
- `experiment_runner.py`, `runner_workflows.py`, `metrics.py`, `storage.py`, `report.py`, `visualization.py`, and `cli.py` remain downstream consumers or orchestrators and must not redefine target-position alignment.
- `schemas.py` remains unchanged because this is an execution input validation rule, not a new runtime schema.

## Scope

- Affected public function: `src/alphaforge/backtest.py::run_backtest`.
- Affected contract: target positions must map unambiguously to market-data row order.
- Accepted inputs:
  - `pd.Series` with index exactly equal to `market_data.index`.
  - list-like or numpy-like values whose length equals the number of market-data rows, assigned positionally.
- Rejected inputs:
  - `pd.Series` with mismatched index labels.
  - any target-position input whose length differs from market data.
- Explicitly out of scope:
  - validation policy
  - permutation null model
  - holdout cutoff
  - max reruns
  - candidate promotion rules
  - GA
  - strategy registry
  - fee, slippage, turnover, strategy, or CLI semantics

## Migration risk

- CLI behavior should remain unchanged for current strategy-generated signals because strategies emit series aligned to the market-data index.
- Existing callers that pass stale-index `pd.Series` will now fail fast with `ValueError` instead of silently aligning.
- Persisted artifact schemas and report formats are unchanged.
- Tests that relied on implicit pandas alignment must be updated to the explicit alignment contract.

## Acceptance conditions

- OpenSpec validates for `stabilize-backtest-target-position-alignment`.
- `run_backtest()` raises `ValueError` when a same-length `pd.Series` has an index that does not equal `market_data.index`.
- `run_backtest()` raises `ValueError` for length mismatches.
- Matching-index `pd.Series` inputs are accepted.
- Same-length list-like or numpy-like inputs are accepted positionally.
- Full pytest passes.
