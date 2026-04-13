# Design: formalize-market-data-schema-and-adapter-boundary

## Canonical ownership mapping

- `src/alphaforge/data_loader.py`
  - Own canonical market-data acceptance, required columns, duplicate policy, missing-data policy, ordering, and post-adapter validation.
- `src/alphaforge/twse_client.py`
  - Own TWSE payload fetching and source-specific normalization into a candidate canonical frame.
- `src/alphaforge/config.py`
  - Provide literal alias maps and policy text only as inputs to the loader; do not treat those literals as the semantic authority.
- `src/alphaforge/strategy/base.py`, `src/alphaforge/strategy/ma_crossover.py`, `src/alphaforge/backtest.py`, `src/alphaforge/metrics.py`, `src/alphaforge/report.py`, `src/alphaforge/visualization.py`, `src/alphaforge/storage.py`, `src/alphaforge/cli.py`, and `src/alphaforge/experiment_runner.py`
  - Consume accepted market data only.

## Contract migration plan

- Keep `load_market_data()` as the post-adapter acceptance gate for every market-data source.
- Keep `twse_client.py` focused on source payload parsing and candidate shaping, not on deciding whether the frame is canonically acceptable.
- Preserve the current canonical OHLCV column order and sort/deduplicate behavior in the loader contract.
- Describe any `config.py` column constants as inputs to the loader, not as a separate business owner.
- Make downstream consumers rely on the loader-accepted frame and treat any extra validation as local safety only.

## Duplicate logic removal plan

- Remove or downgrade any market-data schema wording in downstream modules that implies they own required columns or duplicate policy.
- Remove or downgrade any comments or helper logic in `twse_client.py` that suggest adapter normalization is the final acceptance authority.
- Remove or downgrade any documentation that describes `config.py` constants as the market-data source of truth.
- If a downstream module re-sorts or re-deduplicates the frame with different semantics, collapse that behavior into the loader contract or make it explicitly advisory.

## Verification plan

- Add or update tests that prove:
  - `load_market_data()` returns canonical lower-case OHLCV columns in canonical order,
  - duplicate datetimes are resolved by keeping the last row,
  - the missing-data policy matches the loader contract,
  - TWSE adapter output is only a candidate until the loader accepts it,
  - downstream modules consume accepted frames rather than redefining schema rules.

## Temporary migration states

- If `config.py` still exports `REQUIRED_COLUMNS`, `CSV_COLUMN_ALIASES`, and `MISSING_DATA_POLICY`, treat them as literal inputs only until a later cleanup removes the duplicate surface.
- If `twse_client.py` continues to sort or deduplicate candidate frames, keep that as transport-level shaping only and ensure the loader remains the acceptance authority.
- If downstream modules still contain local defensive checks for column presence, keep them advisory and do not let them become a second schema owner.
