# market-data-schema-and-adapter-boundary Specification

## Purpose
TBD - created by archiving change formalize-market-data-schema-and-adapter-boundary. Update Purpose after archive.
## Requirements
### Requirement: `data_loader.py` is the canonical owner of market-data acceptance

`src/alphaforge/data_loader.py` SHALL be the single authoritative owner of canonical market-data acceptance, including required columns, column meanings, ordering, datetime handling, duplicate handling, missing-data policy, and post-adapter validation.

#### Purpose

- Freeze one market-data contract so CSV ingestion, TWSE ingestion, strategy execution, and downstream reporting all rely on the same accepted runtime shape.
- Prevent `config.py`, `twse_client.py`, or downstream consumers from becoming hidden sources of market-data business semantics.

#### Canonical owner

- `src/alphaforge/data_loader.py` is the only authoritative owner of canonical market-data acceptance and validation.
- `src/alphaforge/config.py` may supply literal alias maps or human-readable policy text as inputs only.
- `src/alphaforge/twse_client.py` is an external adapter only.
- `src/alphaforge/strategy/base.py`, `src/alphaforge/strategy/ma_crossover.py`, `src/alphaforge/strategy/breakout.py`, `src/alphaforge/backtest.py`, `src/alphaforge/metrics.py`, `src/alphaforge/report.py`, `src/alphaforge/visualization.py`, `src/alphaforge/storage.py`, `src/alphaforge/cli.py`, and `src/alphaforge/experiment_runner.py` are downstream consumers only.

#### Allowed responsibilities

- `data_loader.py` MAY:
  - standardize source column names into canonical lower-case names,
  - resolve a source datetime hint into the canonical `datetime` column,
  - parse `datetime` values,
  - sort rows by `datetime` ascending,
  - drop duplicate `datetime` rows by keeping the last occurrence,
  - apply the canonical missing-data policy,
  - validate that the accepted frame is non-empty,
  - validate that canonical OHLCV columns are numeric after cleaning,
  - return a normalized frame ready for strategy and backtest consumption.

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
- Index contract:
  - `datetime` is a canonical column, not the canonical index
  - downstream modules may set an index locally, but the accepted frame is column-based
- Output:
  - a normalized `pd.DataFrame` ready for downstream consumption

#### Invariants

- The accepted market-data frame has exactly one row per `datetime`.
- The accepted market-data frame is sorted in ascending `datetime` order.
- The accepted market-data frame has canonical lower-case OHLCV column names in canonical order.
- The canonical runtime contract is the accepted frame returned by `data_loader.py`, not the raw CSV or adapter payload.

#### Cross-module dependencies

- `config.py` provides literal alias maps and policy text only.
- `twse_client.py` may emit candidate canonical frames that `data_loader.py` then accepts or rejects.
- `experiment_runner.py` calls `load_market_data()` before orchestration.
- `backtest.py`, `metrics.py`, `report.py`, `visualization.py`, `storage.py`, `cli.py`, and `strategy/*` consume accepted market data as authoritative input.

#### Failure modes if this boundary is violated

- If `config.py` and `data_loader.py` both claim schema authority, required columns and alias handling can drift.
- If adapter code owns the acceptance rule, TWSE and CSV paths can normalize the same data differently.
- If downstream modules recheck or reshape market data independently, accepted inputs can stop being interchangeable across workflows.
- If the datetime contract is ambiguous, sorting, duplicate handling, and execution timing assumptions can diverge.

#### Migration notes from current implementation

- `data_loader.py` already standardizes column names, parses datetime, sorts rows, deduplicates timestamps, applies missing-data handling, and validates numeric columns.
- `config.py` currently exposes `REQUIRED_COLUMNS`, `CSV_COLUMN_ALIASES`, and `MISSING_DATA_POLICY` constants that the loader consumes.
- This change makes the loader the explicit authority and treats config constants as inputs rather than the business owner.

#### Open questions / deferred decisions

- Whether `config.py` should keep exporting `REQUIRED_COLUMNS`, `CSV_COLUMN_ALIASES`, and `MISSING_DATA_POLICY` or whether those constants should move into loader-owned implementation helpers is deferred.
  - Recommended default: keep them as literal inputs only until a future cleanup removes the duplicate surface.

#### Scenario: CSV ingestion returns a canonical frame

- GIVEN a CSV file with alias column names, duplicate timestamps, and missing volume values
- WHEN `load_market_data()` accepts the file
- THEN the returned frame SHALL use canonical lower-case column names
- AND the returned frame SHALL be sorted by `datetime`
- AND duplicate timestamps SHALL keep the last row
- AND missing volume SHALL be filled according to the loader policy

#### Scenario: missing required columns fail fast

- GIVEN a candidate market-data frame is missing one of the canonical required columns
- WHEN `load_market_data()` validates the frame
- THEN acceptance SHALL fail fast with an error
- AND no downstream module SHALL treat the frame as accepted market data

### Requirement: `twse_client.py` is an adapter-only source normalization boundary

`src/alphaforge/twse_client.py` SHALL own TWSE payload parsing and source-specific normalization only, and SHALL NOT redefine canonical market-data acceptance rules.

#### Purpose

- Keep source-specific parsing separate from canonical acceptance so TWSE payload changes do not silently change the AlphaForge market-data contract.
- Allow TWSE ingestion to produce a candidate canonical frame without becoming the owner of loader semantics.

#### Canonical owner

- `src/alphaforge/twse_client.py` is the authoritative owner of TWSE payload parsing and TWSE-specific source normalization.
- `src/alphaforge/data_loader.py` remains the authoritative owner of canonical market-data acceptance.

#### Allowed responsibilities

- `twse_client.py` MAY:
  - fetch TWSE payloads,
  - parse source-specific date formats,
  - parse source-specific numeric formats,
  - rename TWSE fields into candidate canonical column names,
  - drop source-only payload fields,
  - drop payload rows that are structurally impossible to normalize,
  - sort or de-duplicate the candidate frame as a transport convenience,
  - emit a candidate frame shaped like canonical OHLCV data.

#### Explicit non-responsibilities

- `twse_client.py` MUST NOT decide the canonical required-column set.
- `twse_client.py` MUST NOT own the canonical duplicate policy.
- `twse_client.py` MUST NOT own the canonical missing-data policy.
- `twse_client.py` MUST NOT decide whether a candidate frame is accepted for downstream consumption.
- `twse_client.py` MUST NOT become a second source of truth for market-data schema semantics.

#### Inputs / outputs / contracts

- Inputs:
  - TWSE remote payloads
  - `TwseFetchRequest`
- Outputs:
  - a candidate market-data frame that may already resemble canonical OHLCV shape
- Contract rules:
  - adapter output is a candidate for `data_loader.py`, not an independently accepted canonical artifact
  - source-specific normalization may occur before loader validation

#### Invariants

- TWSE ingestion is source-specific and adapter-local.
- Adapter output may be shaped like canonical data, but it is not the final authority on canonical acceptance.
- Any loader invariants still apply after adapter output is passed through `data_loader.py`.

#### Cross-module dependencies

- `twse_client.py` depends on the external TWSE payload structure.
- `data_loader.py` consumes adapter output when TWSE data is used as a source.
- `cli.py` may invoke the adapter, but it does not own TWSE normalization semantics.
- Downstream runtime modules consume the loader-accepted frame, not the adapter’s candidate frame.

#### Failure modes if this boundary is violated

- If the adapter owns canonical acceptance, TWSE ingestion can drift from CSV ingestion on the same schema rules.
- If the adapter changes source normalization to imply acceptance semantics, schema bugs can be hidden before the loader sees the data.
- If the adapter begins filling missing data or enforcing required columns, it will duplicate the loader’s business rules.

#### Migration notes from current implementation

- `twse_client.py` already parses TWSE date and numeric fields and emits OHLCV-shaped frames.
- It also currently sorts and deduplicates the candidate frame.
- This change keeps those source-normalization behaviors permitted, but it places canonical acceptance authority in `data_loader.py`.

#### Open questions / deferred decisions

- Whether TWSE adapter deduplication should remain in the adapter for transport convenience or be removed in a later cleanup is deferred.
  - Recommended default: allow transport-level sorting/deduplication only if it does not alter the canonical acceptance rule owned by `data_loader.py`.

#### Scenario: TWSE payloads become candidate canonical frames

- GIVEN a TWSE payload with source-specific date and numeric representations
- WHEN `twse_client.py` normalizes the payload
- THEN the result MAY be shaped like canonical OHLCV columns
- AND the result SHALL still be subject to `data_loader.py` acceptance before downstream use

#### Scenario: adapter output does not override loader acceptance

- GIVEN `twse_client.py` emits a candidate frame
- WHEN the candidate frame is missing required canonical columns or has invalid datetimes
- THEN the frame SHALL NOT be treated as accepted market data until `data_loader.py` validates it

### Requirement: Accepted market data is a downstream runtime contract, not a re-owned schema

Once `data_loader.py` accepts market data, downstream modules SHALL rely on the accepted frame invariants and SHALL NOT silently redefine schema shape, ordering, or duplicate/missing-data policy.

#### Purpose

- Give downstream execution, analytics, reporting, storage, and CLI code a stable market-data contract.
- Prevent later layers from re-normalizing accepted data in ways that diverge from the loader boundary.

#### Canonical owner

- `src/alphaforge/data_loader.py` remains the canonical owner of the market-data contract.
- Downstream modules are consumers only.

#### Allowed responsibilities

- Downstream modules MAY assume:
  - required canonical columns exist,
  - rows are chronologically sorted,
  - duplicate `datetime` values have been resolved,
  - accepted numeric columns are parseable and clean enough for execution and analytics,
  - `datetime` is available as a canonical column.

#### Explicit non-responsibilities

- Downstream modules MUST NOT silently re-normalize accepted market data to a different column set.
- Downstream modules MUST NOT make their own duplicate or missing-data policy decisions for accepted frames.
- Downstream modules MUST NOT treat `config.py` constants or adapter output as a stronger authority than the loader-accepted frame.

#### Inputs / outputs / contracts

- Inputs:
  - loader-accepted market-data frames
- Outputs:
  - execution inputs, analytics inputs, visualization inputs, storage payloads, and CLI artifacts derived from the accepted frame

#### Invariants

- The same accepted frame can flow through strategy, backtest, metrics, report, visualization, storage, and CLI layers without each layer redefining market-data truth.
- Market-data acceptance happens once at the loader boundary.
- Any later module may validate local shape for its own use, but that validation is advisory only and must not redefine the canonical contract.

#### Cross-module dependencies

- `strategy/*` consumes accepted market data for signal generation.
- `backtest.py` consumes accepted market data for execution.
- `metrics.py`, `report.py`, and `visualization.py` consume accepted market data or execution artifacts derived from it.
- `storage.py` serializes outputs derived from accepted market data.
- `cli.py` and `experiment_runner.py` pass accepted data through workflow layers.

#### Failure modes if this boundary is violated

- If downstream modules silently reinterpret accepted data, different workflows can behave differently on the same file.
- If accepted data is re-sorted or deduplicated again with a different rule, execution and analytics can diverge from the loader contract.
- If runtime code starts depending on adapter-specific quirks, TWSE and CSV ingestion will no longer be interchangeable at the accepted-data boundary.

#### Migration notes from current implementation

- Current downstream code already assumes `load_market_data()` returns a cleaned, sorted, unique-datetime frame.
- Visualization and backtest code already rely on canonical OHLCV columns existing after loader acceptance.
- This requirement makes those assumptions explicit and keeps them downstream of the loader boundary.

#### Open questions / deferred decisions

- Whether downstream modules should perform defensive local validation of the accepted frame shape is deferred.
  - Recommended default: allow defensive checks, but keep them advisory and do not let them redefine acceptance semantics.

#### Scenario: downstream execution consumes accepted market data without redefining it

- GIVEN a loader-accepted frame
- WHEN strategy, backtest, metrics, report, visualization, storage, CLI, or orchestration code consumes it
- THEN each module SHALL treat the loader contract as authoritative
- AND no module SHALL redefine the canonical required columns or duplicate policy locally
