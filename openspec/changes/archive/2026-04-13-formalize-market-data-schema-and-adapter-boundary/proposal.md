# Proposal: formalize-market-data-schema-and-adapter-boundary

## Boundary problem

- The repository currently splits market-data responsibility across `data_loader.py`, `twse_client.py`, `config.py`, and downstream consumers that implicitly assume a canonical OHLCV shape.
- `data_loader.py` performs canonical acceptance and cleaning, but `config.py` still exposes required-column and alias constants, and `twse_client.py` already knows enough to shape TWSE payloads into OHLCV-like frames.
- This creates overlap risk around required columns, datetime handling, duplicate handling, missing-data policy, and the point at which a frame becomes authoritative for downstream execution and analytics.

## Canonical ownership decision

- `src/alphaforge/data_loader.py` becomes the single authoritative owner of canonical market-data acceptance.
- `src/alphaforge/twse_client.py` remains an external adapter that may normalize source-specific TWSE payloads into a candidate canonical frame, but it must not redefine canonical acceptance rules.
- `src/alphaforge/config.py` may provide literal alias maps or policy text as inputs only, but it must not be treated as the source of market-data business semantics.
- Downstream modules must consume accepted market data without re-owning schema or cleaning rules.

## Scope

- Affected runtime contracts:
  - required market-data columns
  - column order and meaning
  - datetime parsing and sorting
  - duplicate-row handling
  - missing-data policy
  - acceptance failure behavior
  - adapter-to-loader boundary
- Affected modules:
  - `src/alphaforge/data_loader.py`
  - `src/alphaforge/twse_client.py`
  - `src/alphaforge/config.py`
  - `src/alphaforge/strategy/base.py`
  - `src/alphaforge/strategy/ma_crossover.py`
  - `src/alphaforge/backtest.py`
  - `src/alphaforge/metrics.py`
  - `src/alphaforge/report.py`
  - `src/alphaforge/visualization.py`
  - `src/alphaforge/storage.py`
  - `src/alphaforge/cli.py`
  - `src/alphaforge/experiment_runner.py`

## Migration risk

- If `config.py` remains a hidden source of schema authority, the loader and its callers can drift on required columns or alias handling.
- If `twse_client.py` keeps hardcoding canonical OHLCV semantics beyond source normalization, TWSE ingestion can diverge from CSV-based ingestion.
- If downstream modules assume their own column sets or datetime semantics, report, visualization, or execution code may silently accept frames that do not meet the loader contract.
- If acceptance boundaries are unclear, invalid or partial data may be handled differently depending on whether it arrived from CSV or an external adapter.

## Acceptance conditions

- The spec states one canonical owner for market-data acceptance.
- The spec states exactly which columns are required and what they mean.
- The spec states whether `datetime` is a column or an index in the canonical accepted frame.
- The spec states the authoritative duplicate and missing-data policies.
- The spec states what `twse_client.py` may do as an adapter and what it must not decide.
- The spec states what downstream modules may assume once data is accepted.
