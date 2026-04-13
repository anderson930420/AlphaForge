# Design: formalize-execution-semantics-contract

## Canonical ownership mapping

- `src/alphaforge/backtest.py`
  - Own the signal-to-execution interpretation, one-bar lag, turnover, fees, slippage, trade extraction, and equity construction.
  - Keep the execution contract explicit in function-level docstrings and in any backtest-owned constants or helpers.
- `src/alphaforge/strategy/base.py`
  - Keep only the interface shape for `generate_signals()`.
  - Describe the return type and index compatibility without describing lag or cost behavior.
- `src/alphaforge/strategy/ma_crossover.py`
  - Keep MA crossover signal generation only.
  - Avoid any embedded assumptions about execution lag, cost rules, or trade extraction.
- `src/alphaforge/experiment_runner.py`
  - Continue orchestrating calls into the canonical owners.
  - Do not reconstruct execution outputs or embed timing/cost rules locally.
- `src/alphaforge/metrics.py`
  - Consume backtest outputs for analytics only.
  - Treat turnover and trade count as already-executed artifacts.
- `src/alphaforge/report.py`
  - Render executed outputs.
  - Do not calculate alternate execution artifacts for display.
- `src/alphaforge/visualization.py`
  - Plot executed outputs only.
  - Do not infer trade or cost logic from the chart pipeline.
- `src/alphaforge/storage.py`
  - Serialize the runtime artifacts produced by backtest and metrics owners.
  - Keep persistence schema ownership separate from execution semantics.
- `src/alphaforge/cli.py`
  - Surface execution results and derived artifacts, but not execution rules.
- `src/alphaforge/schemas.py`
  - Retain dataclass containers and shared type definitions only.
  - If a runtime column list remains here, it must be treated as a derived compatibility surface rather than the semantic owner.

## Contract migration plan

- Make the backtest contract the primary source for:
  - target-position normalization,
  - execution lag,
  - turnover,
  - cost application,
  - trade extraction,
  - equity curve construction.
- Update the strategy interface wording so it is read as a target-position contract, not as a generic signal/order contract.
- Update all downstream consumers to describe their dependency as "consumes backtest outputs" rather than "derives execution behavior."
- Preserve the current orchestration call graph in `experiment_runner.py` so the runner remains a caller, not a second semantic owner.

## Duplicate logic removal plan

- Remove or downgrade any duplicate turnover calculation outside `backtest.py`.
- Remove or downgrade any duplicate trade-extraction logic outside `backtest.py`.
- Remove or downgrade any fee/slippage application outside `backtest.py`.
- Remove or downgrade any equity compounding logic outside `backtest.py`.
- Remove or downgrade any comments or docstrings in downstream modules that imply those modules own execution semantics.
- If `schemas.py` still exposes a backtest column list, ensure it is clearly derived from the backtest contract rather than a second source of truth.

## Verification plan

- Add or update tests that prove:
  - the first bar is flat,
  - next-bar execution is enforced,
  - turnover is derived from executed position delta,
  - trade boundaries are detected from position transitions,
  - fees and slippage are applied on turnover,
  - the trade log and turnover are consistent with the same execution path.
- Add or update tests that prove downstream modules only consume the backtest result rather than recomputing execution semantics.
- Add or update tests that cover empty-trade and final-open-trade cases so the canonical output remains stable.

## Temporary migration states

- If current code still carries permissive numeric clipping while the contract is being tightened, treat that behavior as transitional and not as the final semantic owner.
- If any downstream module still has helper logic that resembles execution semantics, keep it only as a thin adapter and add a removal trigger tied to the canonical backtest contract tests.
- If future fractional or short execution is added, require a new spec revision instead of expanding this contract in place.
