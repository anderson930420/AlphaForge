# TWSE Single-Name Backtest Report Demo

This document defines the intended role of the TWSE single-name daily backtest report in AlphaForge.

## Purpose

This demo is an engine-level reporting demonstration, not an alpha claim.

It shows that AlphaForge can ingest real TWSE daily OHLCV data, run a deterministic single-name backtest, apply explicit lagged close-to-close execution semantics, include fee/slippage assumptions, and render equity, drawdown, benchmark, and trade-marker diagnostics.

The MA crossover example is intentionally used as a transparent strategy fixture. It is not presented as evidence of standalone alpha.

## Interpretation

This report should be interpreted as a backtest-engine and reporting artifact.

It is useful even if the MA crossover strategy underperforms buy-and-hold. The important question is not whether the example strategy is profitable, but whether the engine makes assumptions, costs, trades, equity, drawdown, and benchmark-relative behavior visible.

## Cost model boundary

The current backtest uses a symmetric turnover-based fee/slippage model:

```text
turnover x (fee_rate + slippage_rate)
```

This captures a simple fee/slippage assumption, but it does not separately model Taiwan's asymmetric sell-side securities transaction tax. Therefore, the TWSE report should be interpreted as an engine-level cost-assumption demonstration, not a complete Taiwan transaction-cost model.

## Execution semantics boundary

The report uses `signed_close_to_close_lagged`, where realized position follows the previous bar's target position:

```text
position[t] = target_position[t-1]
```

Therefore, trade markers should be interpreted as lagged realized-position changes after the signal, not same-bar execution.

## Validation diagnostics boundary

AlphaForge can compute candidate-level cost sensitivity and bootstrap evidence in validation-style workflows such as `validate-search` and `walk-forward`.

However, those diagnostics are currently persisted in validation/walk-forward artifacts and are not wired into the polished `report.py` card layout through a clean CLI path.

This demo does not attempt to change that architecture.
