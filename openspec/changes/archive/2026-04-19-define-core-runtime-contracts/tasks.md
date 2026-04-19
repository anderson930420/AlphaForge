# Tasks

## 1. Freeze runtime and market-data ownership

- [x] 1.1 Remove the backtest runtime equity-curve column list from `src/alphaforge/schemas.py` and define it in `src/alphaforge/backtest.py`.
- [x] 1.2 Update `src/alphaforge/config.py` and `src/alphaforge/data_loader.py` docstrings/comments so config is clearly constants-only and the loader is clearly the canonical market-data validator.

## 2. Clarify execution and formula ownership

- [x] 2.1 Update `src/alphaforge/strategy/base.py`, `src/alphaforge/strategy/ma_crossover.py`, and `src/alphaforge/backtest.py` docstrings to spell out next-bar target-position semantics and long-flat MVP scope.
- [x] 2.2 Tighten `src/alphaforge/metrics.py`, `src/alphaforge/benchmark.py`, and `src/alphaforge/visualization.py` module docstrings so formula ownership is explicit and non-overlapping.

## 3. Keep runtime, presentation, and persistence layers separated

- [x] 3.1 Confirm `src/alphaforge/report.py` continues to consume explicit presentation inputs only.
- [x] 3.2 Confirm `src/alphaforge/storage.py` continues to own persisted artifact schemas and receipts only.
- [x] 3.3 Confirm `src/alphaforge/experiment_runner.py` and `src/alphaforge/cli.py` remain orchestration-only and payload-assembly-only.

## 4. Lock the contract with tests

- [x] 4.1 Add or update focused tests in `tests/test_backtest.py` to assert the canonical runtime equity-curve columns and trade-log contract.
- [x] 4.2 Keep the current market-data loader tests as the authoritative check for sorting, de-duplication, and missing-data handling.
- [x] 4.3 Run focused regression tests for backtest, data loader, metrics, benchmark, visualization, report, runner, storage, and CLI paths that exercise the frozen contracts.

## 5. Cleanup and documentation

- [x] 5.1 Remove any stale references to the moved runtime column constant.
- [x] 5.2 Update the local worklog and Obsidian notes after the code changes land.
