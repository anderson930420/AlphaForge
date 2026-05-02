# Proposal: harden-backtest-and-data-semantics

## Boundary problem

- AlphaForge's current backtest semantics, trade-log field meanings, and market-data acceptance rules are only partially explicit today.
- The current execution path is close-to-close and lagged, but that contract is implicit in runtime behavior instead of being emitted as metadata.
- Trade-log artifacts currently use return-like values alongside PnL-shaped labels, which makes the persisted schema easier to misread as dollar accounting.
- Market-data acceptance currently tolerates normalization behavior that is not fully spelled out as a canonical quality policy, especially around duplicate datetimes, missing OHLC values, and volume handling.

## Canonical ownership decision

- `src/alphaforge/backtest.py` becomes the canonical owner of the explicit execution semantics metadata and trade extraction semantics.
- `src/alphaforge/data_loader.py` remains the canonical owner of market-data validation and normalization, including the accepted OHLCV quality policy.
- `src/alphaforge/metrics.py` remains the canonical owner of performance formulas, including win rate.
- `src/alphaforge/storage.py` remains the canonical owner of persisted artifact schemas, including the canonical `trade_log.csv` layout and any schema migration markers.
- `src/alphaforge/report.py` remains the canonical owner of display wording only and must not rename return-based trade fields into dollar-PnL language.
- `src/alphaforge/schemas.py` remains passive dataclasses only.

## Scope

- `openspec/specs/execution-semantics-contract/spec.md`
- `openspec/specs/market-data-schema-and-adapter-boundary/spec.md`
- `openspec/specs/research-policy-and-metric-semantics/spec.md`
- `openspec/specs/storage-artifact-ownership/spec.md`
- `openspec/specs/report-view-model-contract/spec.md`
- Public artifact surfaces affected by the change:
  - `trade_log.csv`
  - execution metadata embedded in runtime summaries and persisted artifacts
  - research/report summaries that render trade return labels or execution-semantics labels

## Migration risk

- `trade_log.csv` is a public artifact schema and the field rename is breaking unless a compatibility shim is explicitly added.
- Report wording, fixtures, and any research summaries that currently refer to PnL-style trade labels must be updated in the same controlled migration as the storage schema.
- Tightened market-data validation may reject rows that the current implementation normalizes more loosely, especially on missing OHLC values and duplicate timestamps.
- Execution metadata is now a first-class contract, so any consumer that infers semantics from runtime behavior alone will need to derive from the emitted metadata instead.

## Acceptance conditions

- The change uses deltas against the existing canonical specs rather than creating a new `*-v2` canonical spec folder.
- Execution semantics, trade-return semantics, and market-data quality rules are each assigned one canonical owner.
- The spec explicitly states the public artifact schema risk for `trade_log.csv` and the coordinated update expectation for downstream labels and summaries.
- `openspec validate harden-backtest-and-data-semantics --type change --no-interactive` passes.
