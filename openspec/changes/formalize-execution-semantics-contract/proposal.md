# Proposal: formalize-execution-semantics-contract

## Boundary problem

- `Strategy.generate_signals()` currently reads like a generic target-position interface, but the actual execution law is spread across `backtest.py`, strategy implementations, metrics, report rendering, storage, and orchestration code.
- The current backtest path implicitly decides how signals are coerced, filled, clipped, lagged, and converted into positions, turnover, trades, costs, and equity, but those rules are not fully stated as a contract.
- This leaves room for drift between the strategy interface wording, the backtest executor, and downstream consumers that read the executed results.

## Canonical ownership decision

- `src/alphaforge/backtest.py` becomes the single authoritative owner of execution semantics.
- The following modules must stop owning or redefining execution rules:
  - `src/alphaforge/strategy/base.py`
  - `src/alphaforge/strategy/ma_crossover.py`
  - `src/alphaforge/experiment_runner.py`
  - `src/alphaforge/metrics.py`
  - `src/alphaforge/report.py`
  - `src/alphaforge/visualization.py`
  - `src/alphaforge/storage.py`
  - `src/alphaforge/cli.py`
- `src/alphaforge/schemas.py` may continue to define in-memory containers, but it must not become the semantic owner of execution behavior.

## Scope

- Affected runtime contracts:
  - strategy-output interpretation
  - target-position normalization
  - position lag and anti-lookahead timing
  - turnover derivation
  - fee and slippage application
  - trade boundary detection and extraction
  - equity-curve construction
  - backtest-produced trade-log schema
- Affected modules:
  - `src/alphaforge/backtest.py`
  - `src/alphaforge/strategy/base.py`
  - `src/alphaforge/strategy/ma_crossover.py`
  - `src/alphaforge/experiment_runner.py`
  - `src/alphaforge/metrics.py`
  - `src/alphaforge/report.py`
  - `src/alphaforge/visualization.py`
  - `src/alphaforge/storage.py`
  - `src/alphaforge/cli.py`
  - `src/alphaforge/schemas.py`
  - tests and docs that currently restate execution rules implicitly

## Migration risk

- Changing execution semantics can alter:
  - equity curves,
  - trade counts,
  - turnover,
  - Sharpe and drawdown inputs,
  - stored CSV contents,
  - HTML report summaries,
  - CLI-visible artifacts,
  - regression test expectations.
- Any ambiguity between binary long-flat execution and fractional exposure handling can produce silent behavior drift unless the contract is stated explicitly in one place.
- If same-bar execution is accidentally introduced, results will become lookahead-biased and will no longer match the existing runtime contract.

## Acceptance conditions

- The spec states one canonical owner for execution semantics and lists every downstream consumer as non-owning.
- The spec states the canonical meaning of `generate_signals()` output, including normalization, index alignment, and supported value domain.
- The spec states the anti-lookahead rule, including first-bar behavior.
- The spec states how turnover, trade extraction, fees, slippage, and equity are derived from executed positions.
- The spec states which execution outputs are canonical runtime artifacts and which modules only consume them.
- The spec includes deferred decisions only where the repo still leaves a real semantic choice open.
