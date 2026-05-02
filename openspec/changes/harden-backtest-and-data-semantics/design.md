# Design: harden-backtest-and-data-semantics

## Canonical ownership mapping

- `src/alphaforge/backtest.py`
  - Owns the explicit execution semantics contract for `legacy_close_to_close_lagged`.
  - Owns trade extraction semantics and the canonical interpretation of trade return fields.
- `src/alphaforge/data_loader.py`
  - Owns canonical OHLCV acceptance and quality policy before research use.
  - Owns duplicate-datetime collapse behavior and missing-data handling policy for accepted market data.
- `src/alphaforge/metrics.py`
  - Owns win-rate computation from return-based trade data.
- `src/alphaforge/storage.py`
  - Owns the persisted `trade_log.csv` schema and any schema-version or compatibility metadata.
- `src/alphaforge/report.py`
  - Owns display wording and must render the return-based trade fields without relabeling them as dollar PnL.

## Contract migration plan

- Make execution semantics explicit as metadata instead of only being an implied runtime behavior.
- Move the canonical trade log to a return-based schema and treat the old PnL-shaped labels as legacy only.
- Keep market-data normalization centered in `data_loader.py`, but make the accepted quality policy explicit enough that downstream execution, storage, and reporting layers can rely on it without reinterpreting the input.
- Preserve the separation between runtime contracts and persisted artifact schemas by letting `storage.py` serialize the new field names and metadata rather than teaching runtime modules to infer them from file layout.

## Duplicate logic removal plan

- Remove any remaining PnL-shaped trade-log labels from the canonical persisted schema.
- Remove any downstream assumptions that trade-log values represent dollar accounting instead of return contributions.
- Remove implicit market-data acceptance rules from consumers outside `data_loader.py`.
- Remove any report wording that turns the new return-based trade fields back into profit-and-loss language.

## Verification plan

- Validate the change against the existing canonical specs before implementation.
- Later runtime verification should confirm:
  - execution metadata is emitted with the exact semantic labels in the spec,
  - trade-log schema fields match the return-based contract,
  - win rate is computed from positive `trade_net_return` values,
  - OHLC missing values fail by default,
  - duplicate datetime handling is deterministic and recorded.

## Temporary migration states

- Prefer a single coordinated rename for `trade_log.csv` rather than a long-lived dual schema.
- If a temporary compatibility reader is required, it must be explicit legacy-only behavior and must not become the canonical output contract.
- Report labels and research summaries should be updated in the same controlled change as the storage schema so the repo does not expose both PnL-shaped and return-based canonical wording at once.
