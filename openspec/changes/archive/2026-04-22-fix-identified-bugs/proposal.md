# Proposal: fix-identified-bugs

## Boundary problem

- `src/alphaforge/scoring.py` references `Any` in its ranking-key annotation without importing it, which leaves a backtest-adjacent implementation detail undefined under strict annotation handling.
- `src/alphaforge/backtest.py` owns trade extraction semantics, but `_extract_trades()` currently realizes that contract through a Python row loop rather than a vectorized pandas path, which turns a canonical execution rule into a scaling bottleneck on large frames.
- `src/alphaforge/permutation.py` owns the permutation diagnostic, but its strategy builder and CLI path are still effectively MA-only even though the canonical supported family set already lives in `src/alphaforge/search.py` and the repo now supports `breakout`.
- `src/alphaforge/metrics.py` owns Sharpe-ratio semantics, but `_compute_sharpe_ratio()` currently uses raw returns instead of excess per-period returns, so the implementation does not match the expected performance-analytics contract.

## Canonical ownership decision

- `src/alphaforge/scoring.py` remains the canonical owner of result ranking implementation details and must carry the imports required by its own annotations.
- `src/alphaforge/backtest.py` remains the canonical owner of trade-boundary detection and forced final-bar exits; the implementation will be vectorized without moving those semantics elsewhere.
- `src/alphaforge/search.py` remains the canonical owner of the supported strategy-family set, while `src/alphaforge/permutation.py` remains the canonical owner of permutation diagnostics and must consume that family set instead of redefining it.
- `src/alphaforge/cli.py` remains the canonical owner of `permutation-test` argument parsing and request assembly, including explicit strategy-family selection for that command.
- `src/alphaforge/metrics.py` remains the canonical owner of Sharpe-ratio semantics, including interpretation of `risk_free_rate` as a per-period rate with a backward-compatible default of `0.0`.

## Scope

- OpenSpec boundary deltas for:
  - execution trade extraction semantics
  - performance analytics semantics
  - permutation diagnostic strategy-family support
  - CLI request assembly for `permutation-test`
- Code changes in:
  - `src/alphaforge/scoring.py`
  - `src/alphaforge/backtest.py`
  - `src/alphaforge/permutation.py`
  - `src/alphaforge/cli.py`
  - `src/alphaforge/metrics.py`
- Test updates in:
  - `tests/test_backtest.py`
  - `tests/test_permutation.py`
  - `tests/test_metrics.py`
  - `tests/test_cli.py`

## Migration risk

- The vectorized trade extractor must preserve the current long/flat transition semantics exactly, including empty frames, always-flat inputs, and forced final-row exits, or trade logs and downstream metrics will drift.
- Extending permutation diagnostics to `breakout` changes the accepted CLI surface for `permutation-test`; if CLI assembly and diagnostic strategy construction diverge, the command can parse successfully but fail at runtime for a supported family.
- Adding `risk_free_rate` to metric functions must not change existing callers that rely on the default behavior, and it must not leak into `BacktestConfig` or `MetricReport` field names in this change.
- The scoring import fix is low risk but must remain local to `scoring.py` so no schema-owned contracts are touched.

## Acceptance conditions

- `proposal.md`, `design.md`, and `tasks.md` exist for `fix-identified-bugs`, and the boundary deltas name the canonical owners for the affected rules.
- `_extract_trades()` is implemented with vectorized pandas operations while preserving the current trade-log contract and edge-case behavior.
- `permutation-test` accepts `--strategy` using the same CLI style as the rest of AlphaForge and can build either `ma_crossover` or `breakout` through the diagnostic owner.
- `compute_metrics()` and `_compute_sharpe_ratio()` accept a per-period `risk_free_rate` defaulting to `0.0`, and existing call sites remain backward compatible.
- `pytest` passes with focused coverage for the four confirmed bugs only.
