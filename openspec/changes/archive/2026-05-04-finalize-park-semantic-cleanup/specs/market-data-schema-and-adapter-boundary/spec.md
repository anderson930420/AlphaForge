# Delta for Market Data Schema and Adapter Boundary Cleanup

## MODIFIED Requirements

### Requirement: `data_loader.py` is the canonical owner of market-data acceptance

`src/alphaforge/data_loader.py` SHALL be the single authoritative owner of canonical market-data acceptance, including required columns, column meanings, ordering, datetime handling, duplicate handling, missing-data policy, and post-adapter validation.

#### Allowed responsibilities

- `data_loader.py` MAY:
  - standardize source column names into canonical lower-case names,
  - resolve a source datetime hint into the canonical `datetime` column,
  - parse `datetime` values,
  - sort rows by `datetime` ascending,
  - fail canonical OHLCV input that contains duplicate `datetime` values,
  - apply the canonical missing-data policy,
  - validate that the accepted frame is non-empty,
  - validate that canonical OHLCV columns are numeric after cleaning,
  - validate that `open`, `high`, `low`, and `close` are finite positive values,
  - validate that `high >= low`, `high >= open`, `high >= close`, `low <= open`, and `low <= close`,
  - return a normalized frame ready for strategy and backtest consumption,
  - emit a data-quality summary that downstream storage and report owners may persist or display.

#### Explicit non-responsibilities

- `data_loader.py` MUST NOT silently collapse duplicate datetimes with keep-last or any other repair rule.
- `data_loader.py` MUST NOT own strategy semantics, execution semantics, benchmark semantics, report rendering, or persistence layout.
- `config.py` MUST NOT be treated as the canonical owner of market-data business semantics just because it exports literal constants.
- `twse_client.py` MUST NOT define the canonical acceptance rule for required columns, duplicates, or missing data.
- Downstream modules MUST NOT redefine loader acceptance rules or silently re-normalize schema shape.

#### Inputs / outputs / contracts

- Required canonical columns:
  - `datetime`
  - `open`
  - `high`
  - `low`
  - `close`
  - `volume`
- Duplicate handling:
  - source duplicate datetimes SHALL be rejected as invalid research input
  - the accepted frame SHALL have unique, strictly increasing `datetime` values
  - duplicate rejection SHALL be explicit in the data-quality summary or error context
- Missing-data policy:
  - missing OHLC values SHALL fail by default
  - missing volume values SHALL be normalized according to an explicit loader policy, with the current canonical policy recorded in the data-quality summary

#### Invariants

- The accepted market-data frame has exactly one row per `datetime`.
- The accepted market-data frame is sorted in ascending `datetime` order.
- The accepted market-data frame has canonical lower-case OHLCV column names in canonical order.
- The accepted market-data frame has finite positive OHLC values.

#### Scenario: duplicate datetimes fail fast

- GIVEN a CSV file with canonical OHLCV columns and duplicate `datetime` rows
- WHEN `data_loader.py` validates the file
- THEN the loader SHALL fail
- AND it SHALL identify duplicate datetime as invalid research input
- AND it SHALL NOT silently repair the input by keeping the last row

