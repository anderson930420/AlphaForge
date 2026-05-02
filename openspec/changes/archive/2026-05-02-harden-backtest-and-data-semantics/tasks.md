# Tasks

## 1. Spec and contract alignment

- [x] 1.1 Update the execution-semantics-contract delta to name the legacy close-to-close lagged execution semantics and the return-based trade-log contract.
- [x] 1.2 Update the market-data-schema-and-adapter-boundary delta to make OHLCV quality rules, duplicate collapse, and volume handling explicit.
- [x] 1.3 Update the metric, storage, and report boundary deltas so win rate, persisted trade-log shape, and display wording all derive from the canonical return-based trade contract.

## 2. Migration design

- [x] 2.1 Keep the canonical owners limited to backtest, data_loader, metrics, storage, and report.
- [x] 2.2 Preserve the change as a coordinated contract migration rather than a new execution simulator or data platform.
- [x] 2.3 Record the public artifact schema risk for `trade_log.csv` and the downstream impact on research/report artifacts.

## 3. Verification

- [x] 3.1 Run `openspec validate harden-backtest-and-data-semantics --type change --no-interactive`.
- [x] 3.2 Confirm the change does not introduce next-open, MOC, intraday, shorting, leverage, multi-asset, or broker-like execution semantics.

## 4. Future implementation follow-up

- [x] 4.1 Implement runtime metadata emission for the execution semantics contract.
- [x] 4.2 Implement the return-based trade-log schema and update downstream serializers, report labels, and fixtures in one controlled change.
- [x] 4.3 Tighten market-data validation and attach a data-quality summary through the storage-owned artifact path.
