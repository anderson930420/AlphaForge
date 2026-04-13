# Tasks

## 1. Spec and contract alignment

- [ ] 1.1 Update the execution-semantics proposal and spec so `src/alphaforge/backtest.py` is the only authoritative owner of timing, turnover, cost, trade, and equity semantics.
- [ ] 1.2 Update `src/alphaforge/strategy/base.py` and `src/alphaforge/strategy/ma_crossover.py` wording so the strategy layer is clearly an input producer, not an execution-law owner.
- [ ] 1.3 Identify every downstream consumer that must treat backtest outputs as derived artifacts only: `metrics.py`, `report.py`, `visualization.py`, `storage.py`, `cli.py`, and `experiment_runner.py`.

## 2. Code migration

- [ ] 2.1 Move any remaining implicit execution constants or normalization helpers into `src/alphaforge/backtest.py`.
- [ ] 2.2 Remove or downgrade duplicate turnover, trade, cost, or equity calculations in non-owning modules.
- [ ] 2.3 Update orchestration, persistence, reporting, and visualization code to consume the canonical backtest outputs instead of reconstructing them.

## 3. Verification

- [ ] 3.1 Add or update tests that prove the execution contract is next-bar, long-flat only, and anti-lookahead by construction.
- [ ] 3.2 Add or update tests that prove turnover, trade extraction, fee/slippage application, and equity compounding all originate from the same backtest path.
- [ ] 3.3 Add or update tests that prove metrics, reports, storage, and CLI outputs agree on the same executed artifact shape.

## 4. Cleanup

- [ ] 4.1 Remove stale comments or docstrings that imply strategy modules, metrics, or orchestration own execution semantics.
- [ ] 4.2 Update any derived documentation or worklog references so they point readers to the backtest contract as the source of truth.
