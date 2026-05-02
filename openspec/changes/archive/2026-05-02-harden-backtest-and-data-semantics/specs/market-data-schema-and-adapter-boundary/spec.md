# Delta for Market Data Schema and Adapter Boundary

## MODIFIED Requirements

### Requirement: `data_loader.py` is the canonical owner of market-data acceptance

`src/alphaforge/data_loader.py` SHALL be the single authoritative owner of canonical market-data acceptance, including required columns, column meanings, ordering, datetime handling, duplicate handling, missing-data policy, and post-adapter validation.

#### Purpose

- Freeze one market-data contract so CSV ingestion, TWSE ingestion, strategy execution, and downstream reporting all rely on the same accepted runtime shape.
- Prevent `config.py`, `twse_client.py`, or downstream consumers from becoming hidden sources of market-data business semantics.

#### Canonical owner

- `src/alphaforge/data_loader.py` is the only authoritative owner of canonical market-data acceptance and validation.
- `src/alphaforge/config.py` may supply literal alias maps or human-readable policy text as inputs only.
- `src/alphaforge/twse_client.py` is an external adapter only.
- `src/alphaforge/strategy/base.py`, `src/alphaforge/strategy/ma_crossover.py`, `src/alphaforge/backtest.py`, `src/alphaforge/metrics.py`, `src/alphaforge/report.py`, `src/alphaforge/visualization.py`, `src/alphaforge/storage.py`, `src/alphaforge/cli.py`, and `src/alphaforge/experiment_runner.py` are downstream consumers only.

#### Allowed responsibilities

- `data_loader.py` MAY:
  - standardize source column names into canonical lower-case names,
  - resolve a source datetime hint into the canonical `datetime` column,
  - parse `datetime` values,
  - sort rows by `datetime` ascending,
  - deterministically collapse duplicate `datetime` rows by keeping the last normalized row,
  - apply the canonical missing-data policy,
  - validate that the accepted frame is non-empty,
  - validate that canonical OHLCV columns are numeric after cleaning,
  - validate that `open`, `high`, `low`, and `close` are finite positive values,
  - validate that `high >= low`, `high >= open`, `high >= close`, `low <= open`, and `low <= close`,
  - return a normalized frame ready for strategy and backtest consumption,
  - emit a data-quality summary that downstream storage and report owners may persist or display.

#### Explicit non-responsibilities

- `data_loader.py` MUST NOT own strategy semantics, execution semantics, benchmark semantics, report rendering, or persistence layout.
- `config.py` MUST NOT be treated as the canonical owner of market-data business semantics just because it exports literal constants.
- `twse_client.py` MUST NOT define the canonical acceptance rule for required columns, duplicates, or missing data.
- Downstream modules MUST NOT redefine loader acceptance rules or silently re-normalize schema shape.

#### Inputs / outputs / contracts

- Inputs:
  - `DataSpec.path`
  - `DataSpec.datetime_column`
  - CSV or adapter-produced candidate canonical market-data frames
- Required canonical columns:
  - `datetime`
  - `open`
  - `high`
  - `low`
  - `close`
  - `volume`
- Canonical column naming convention:
  - lower-case ASCII column names
  - canonical order exactly `datetime`, `open`, `high`, `low`, `close`, `volume`
- Canonical column meanings:
  - `datetime`: timestamp for the market bar
  - `open`: bar open price
  - `high`: bar high price
  - `low`: bar low price
  - `close`: bar close price
  - `volume`: bar traded volume
- Semantic type expectations:
  - `datetime` must be parseable to a pandas datetime dtype
  - price and volume columns must be numeric after acceptance
- Duplicate handling:
  - source duplicate datetimes MAY be accepted only if they are collapsed deterministically during normalization
  - the accepted frame MUST have unique, strictly increasing `datetime` values
  - duplicate collapse policy SHALL be explicit in the data-quality summary
- Missing-data policy:
  - missing OHLC values SHALL fail by default
  - missing volume values SHALL be normalized according to an explicit loader policy, with the current canonical policy recorded in the data-quality summary
- Output:
  - a normalized `pd.DataFrame` ready for downstream consumption
  - a data-quality summary or metadata payload that storage may persist through its own serializer

#### Invariants

- The accepted market-data frame has exactly one row per `datetime`.
- The accepted market-data frame is sorted in ascending `datetime` order.
- The accepted market-data frame has canonical lower-case OHLCV column names in canonical order.
- The accepted market-data frame has finite positive OHLC values.
- The canonical runtime contract is the accepted frame returned by `data_loader.py`, not the raw CSV or adapter payload.

#### Cross-module dependencies

- `config.py` provides literal alias maps and policy text only.
- `twse_client.py` may emit candidate canonical frames that `data_loader.py` then accepts or rejects.
- `experiment_runner.py` calls `load_market_data()` before orchestration.
- `backtest.py`, `metrics.py`, `report.py`, `visualization.py`, `storage.py`, `cli.py`, and `strategy/*` consume accepted market data as authoritative input.
- `storage.py` may persist the data-quality summary, but it does not own the acceptance rule.

#### Failure modes if this boundary is violated

- If `config.py` and `data_loader.py` both claim schema authority, required columns and alias handling can drift.
- If adapter code owns the acceptance rule, TWSE and CSV paths can normalize the same data differently.
- If downstream modules recheck or reshape market data independently, accepted inputs can stop being interchangeable across workflows.
- If the datetime contract is ambiguous, sorting, duplicate handling, and execution timing assumptions can diverge.
- If OHLC missing values are silently filled, strategy and backtest results can appear valid even when the input quality is not.

#### Migration notes from current implementation

- `data_loader.py` already standardizes column names, parses datetime, sorts rows, deduplicates timestamps, applies missing-data handling, and validates numeric columns.
- This change makes duplicate collapse and OHLC quality checks explicit, and it requires the missing-data policy to be spelled out rather than implied.

#### Open questions / deferred decisions

- Whether the explicit missing-volume policy should remain zero-fill or move to a stricter rejection rule is deferred.
  - Recommended default: keep the current zero-fill policy only if the data-quality summary records it unambiguously.

#### Scenario: CSV ingestion returns a canonical frame

- GIVEN a CSV file with alias column names and duplicate timestamps
- WHEN `load_market_data()` accepts the file
- THEN the returned frame SHALL use canonical lower-case column names
- AND the returned frame SHALL be sorted by `datetime`
- AND duplicate timestamps SHALL be collapsed deterministically by keeping the last normalized row
- AND the accepted frame SHALL have unique, strictly increasing `datetime` values

#### Scenario: missing required columns or invalid OHLC values fail fast

- GIVEN a candidate market-data frame is missing one of the canonical required columns
- OR a candidate market-data frame contains missing OHLC values
- OR a candidate market-data frame contains non-finite or non-positive OHLC values
- WHEN `load_market_data()` validates the frame
- THEN acceptance SHALL fail fast with an error
- AND no downstream module SHALL treat the frame as accepted market data
