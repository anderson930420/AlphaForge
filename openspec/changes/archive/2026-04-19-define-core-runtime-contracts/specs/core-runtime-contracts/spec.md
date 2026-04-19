# Delta for Core Runtime Contracts

## ADDED Requirements

### Requirement: `config.py` owns literal defaults and input-policy constants only

`src/alphaforge/config.py` SHALL own literal defaults, ranges, aliases, and human-readable input-policy constants, and SHALL NOT be treated as the canonical owner of validation, execution, metric, benchmark, or artifact semantics.

#### Purpose

- Keep shared constants available without turning `config.py` into a hidden business-logic owner.
- Make it explicit that config values are inputs to authoritative layers, not the authority for the rules themselves.

#### Canonical owner

- `src/alphaforge/config.py` is the single authoritative owner of:
  - default capital, fee, slippage, seed, and annualization values
  - short/long window ranges
  - raw column alias mappings
  - the canonical missing-data policy text used by the loader
- `src/alphaforge/data_loader.py` remains the authoritative validator and normalizer that consumes those constants.

#### Allowed responsibilities

- Store literal scalar defaults and raw input constants.
- Export default ranges used by search and CLI argument defaults.
- Export policy text or alias maps that other layers consume.

#### Explicit non-responsibilities

- `config.py` MUST NOT validate market data.
- `config.py` MUST NOT normalize CSV content.
- `config.py` MUST NOT define runtime execution semantics.
- `config.py` MUST NOT own metric or benchmark formulas.
- `config.py` MUST NOT own persisted artifact naming or layout.

#### Inputs / outputs / contracts

- Inputs:
  - none beyond import-time constants
- Outputs:
  - `INITIAL_CAPITAL`
  - `DEFAULT_FEE_RATE`
  - `DEFAULT_SLIPPAGE_RATE`
  - `DEFAULT_RANDOM_SEED`
  - `DEFAULT_ANNUALIZATION`
  - `SHORT_WINDOW_RANGE`
  - `LONG_WINDOW_RANGE`
  - `REQUIRED_COLUMNS`
  - `CSV_COLUMN_ALIASES`
  - `MISSING_DATA_POLICY`
- Consumption boundary:
  - `data_loader.py` MAY consume `REQUIRED_COLUMNS`, `CSV_COLUMN_ALIASES`, and `MISSING_DATA_POLICY`
  - `cli.py` MAY consume the default values for argument defaults

#### Invariants

- `config.py` only exposes literal values and descriptive policy text.
- Any rule that can affect execution semantics, validation semantics, metrics, or artifact layout MUST live in another canonical owner.

#### Cross-module dependencies

- `data_loader.py` depends on `config.py` for literal column-policy constants.
- `experiment_runner.py` and `cli.py` depend on `config.py` for default values only.

#### Failure modes if this boundary is violated

- Config constants drift into ad hoc business rules.
- CLI defaults and validation behavior stop matching the actual loader or executor semantics.
- Reloading the same constants from multiple modules creates a false sense of authority.

#### Migration notes from current implementation

- The literal constants already exist and are used in the current loader and CLI paths.
- This change only freezes the ownership rule so the constants remain inputs, not authority.

#### Open questions / deferred decisions

- Whether literal defaults should eventually move into a typed settings object is deferred.

### Requirement: Market data canonical schema is owned by `data_loader.py`

`src/alphaforge/data_loader.py` SHALL be the authoritative validator and normalizer for market data, and `src/alphaforge/backtest.py` SHALL consume validated market data without re-owning the cleaning rules.

#### Purpose

- Define one canonical market-data contract for AlphaForge.
- Prevent data cleaning rules from being split between config, loader, backtest, report, or visualization code.

#### Canonical owner

- `src/alphaforge/data_loader.py` is the single authoritative owner of market-data validation and normalization.
- `src/alphaforge/config.py` supplies literal constants only.
- `src/alphaforge.schemas.DataSpec` describes the input file location and datetime-column hint, not the data-cleaning semantics.

#### Allowed responsibilities

- `data_loader.py` MAY:
  - standardize column names,
  - resolve datetime aliases,
  - parse datetime values,
  - sort ascending by datetime,
  - drop duplicate datetime rows by keeping the last occurrence,
  - apply the missing-data policy,
  - validate numeric OHLCV columns,
  - reject empty frames after cleaning.
- `backtest.py` MAY assume the returned frame is already normalized and may only consume it as validated input.

#### Explicit non-responsibilities

- `backtest.py` MUST NOT infer market-data shape rules from execution side effects.
- `report.py`, `visualization.py`, and `storage.py` MUST NOT define market-data cleaning rules.
- `schemas.py` MUST NOT own dataframe-cleaning semantics.

#### Inputs / outputs / contracts

- Required market-data columns:
  - `datetime`
  - `open`
  - `high`
  - `low`
  - `close`
  - `volume`
- Duplicate-row policy:
  - rows are sorted by `datetime`
  - duplicate `datetime` values are resolved by keeping the last row for that timestamp
- Missing-data policy boundary:
  - rows missing `datetime` or `close` are removed
  - `open`, `high`, `low`, and `close` are forward-filled after sorting
  - missing `volume` is filled with `0`
  - remaining rows with missing price columns are removed
- Validation boundary:
  - `data_loader.py` is authoritative for shape and cleaning
  - downstream consumers SHALL treat the returned frame as validated input

#### Invariants

- `load_market_data()` returns a frame sorted in ascending datetime order.
- `load_market_data()` returns a frame with unique datetimes.
- All returned OHLCV columns are numeric.
- The canonical market-data contract is the cleaned frame returned by `data_loader.py`, not the raw CSV.

#### Cross-module dependencies

- `backtest.py` depends on `data_loader.py` output.
- `experiment_runner.py` depends on `data_loader.py` for loading before orchestration.
- `cli.py` and `twse_client.py` may create or save CSVs, but they do not own market-data cleaning semantics.

#### Failure modes if this boundary is violated

- Different modules normalize the same CSV differently.
- Duplicate rows or missing values are treated inconsistently between search, validation, and reporting workflows.
- Backtest results become dependent on accidental preprocessing details rather than the canonical loader contract.

#### Migration notes from current implementation

- The current loader already standardizes columns, sorts, de-duplicates, and applies missing-data policy.
- This change makes that behavior explicitly canonical and prevents later layers from reinterpreting it.

#### Open questions / deferred decisions

- Whether additional source formats beyond CSV should share the same canonical normalization boundary is deferred.

### Requirement: Strategy signal and backtest execution semantics are backtest-owned

`src/alphaforge/strategy/base.py`, `src/alphaforge/strategy/ma_crossover.py`, and `src/alphaforge/backtest.py` SHALL define the strategy target-position interface and the execution law for the MVP long-flat strategy family.

#### Purpose

- Freeze how a strategy signal turns into a backtest position.
- Remove ambiguity about same-bar versus next-bar interpretation.
- Keep execution law in one owner instead of spreading it across strategy code, runner code, or presentation code.

#### Canonical owner

- `src/alphaforge/strategy/base.py` is the interface owner for `generate_signals()`.
- `src/alphaforge/strategy/ma_crossover.py` is the canonical MVP implementation of the long-flat crossover strategy.
- `src/alphaforge/backtest.py` is the canonical owner of execution semantics, trade extraction, and the runtime equity-curve / trade-log output contract.

#### Allowed responsibilities

- `Strategy.generate_signals()` MAY return a `pd.Series` aligned to the input market-data index.
- MVP strategy implementations MAY emit long-flat target positions only.
- `backtest.py` MAY:
  - clamp target positions into the long-flat range for defensive safety,
  - shift target positions by one bar before applying them,
  - compute close-to-close returns,
  - compute turnover from position changes,
  - apply fee and slippage costs on turnover,
  - compound equity multiplicatively,
  - close any open trade on the final sample bar.
- `backtest.py` MAY emit a runtime equity curve containing both source market-data columns and backtest-derived columns.

#### Explicit non-responsibilities

- `Strategy` implementations MUST NOT own fee application, slippage application, turnover calculation, or trade extraction.
- `backtest.py` MUST NOT reinterpret next-bar signals as same-bar fills.
- `report.py`, `visualization.py`, `storage.py`, and `cli.py` MUST NOT redefine strategy signal semantics.
- `metrics.py` and `benchmark.py` MUST NOT own execution timing semantics.

#### Inputs / outputs / contracts

- Strategy signal contract:
  - `generate_signals()` returns a `pd.Series`
  - the series is indexed like the input market data
  - the series values represent target position for the next tradable interval
  - in the current MVP, valid target-position values are `0.0` and `1.0`
  - long-flat-only behavior is part of the formal contract for the current MVP
- Backtest execution semantics:
  - `position = target_position.shift(1)`
  - close-to-close returns are computed from `close.pct_change()`
  - turnover is the absolute change in position, with the initial position treated as opening turnover
  - trading cost is `turnover * (fee_rate + slippage_rate)`
  - strategy return is `position * close_return - trading_cost`
  - equity is compounded as `initial_capital * cumprod(1 + strategy_return)`
  - any open trade at the final sample is closed at the final close
- Canonical runtime backtest output columns:
  - `datetime`
  - `open`
  - `high`
  - `low`
  - `close`
  - `volume`
  - `target_position`
  - `position`
  - `close_return`
  - `turnover`
  - `strategy_return`
  - `equity`
- Canonical runtime trade log contract:
  - `entry_time`
  - `exit_time`
  - `side`
  - `quantity`
  - `entry_price`
  - `exit_price`
  - `gross_return`
  - `net_pnl`

#### Invariants

- The runtime equity curve is a backtest-owned contract, not a schema constant owned by `schemas.py`.
- The trade log is a backtest-generated runtime record stream that storage may serialize, but storage does not define the trade semantics.
- Strategy signals are next-bar target positions, not fill instructions for the current bar.
- The MVP remains long-flat only; any future extension to shorts or leverage requires a new spec.

#### Cross-module dependencies

- `strategy.base.py` depends on `schemas.py` for `StrategySpec`.
- `backtest.py` depends on validated market data from `data_loader.py`.
- `metrics.py` consumes `backtest.py` outputs.
- `storage.py` serializes the runtime outputs after execution.
- `visualization.py` and `report.py` may consume the runtime outputs, but they do not own the law that produced them.

#### Failure modes if this boundary is violated

- Same-bar and next-bar semantics drift across strategies and tests.
- Fee and slippage handling diverges between execution and reporting.
- Backtest output shape becomes a schema accident instead of a canonical runtime contract.
- Trade extraction can change without any change in execution semantics, making debugging difficult.

#### Migration notes from current implementation

- `MovingAverageCrossoverStrategy` already emits long-flat signals.
- `run_backtest()` already shifts target positions by one bar and computes close-to-close returns.
- The backtest-equity runtime column list must live in `backtest.py` rather than `schemas.py` after this change.

#### Open questions / deferred decisions

- Whether future strategy families should still share the same next-bar target-position interface when shorts or leverage are added is deferred.

### Requirement: Strategy metrics and benchmark formulas have separate canonical owners

`src/alphaforge/metrics.py` and `src/alphaforge/benchmark.py` SHALL own strategy metrics and benchmark summary formulas respectively, and `src/alphaforge/visualization.py` SHALL treat drawdown series as display-only derivations.

#### Purpose

- Prevent strategy metrics, benchmark metrics, and plot-only series from sharing a hidden formula owner.
- Make it obvious which module is authoritative for each formula used in ranking, validation, and reporting.

#### Canonical owner

- `src/alphaforge/metrics.py` is the single authoritative owner of strategy metric formulas.
- `src/alphaforge/benchmark.py` is the single authoritative owner of benchmark equity construction, benchmark total return, benchmark max drawdown, and benchmark summary normalization.
- `src/alphaforge/visualization.py` is the single authoritative owner of presentation-only chart transformations.

#### Allowed responsibilities

- `metrics.py` MAY compute:
  - total return
  - annualized return
  - Sharpe ratio
  - max drawdown
  - win rate
  - turnover
  - trade count
- `benchmark.py` MAY compute:
  - buy-and-hold equity curves
  - benchmark total return
  - benchmark max drawdown
  - benchmark summary normalization
- `visualization.py` MAY derive drawdown series for plotting and may transform already-computed frames into chart-ready series.

#### Explicit non-responsibilities

- `metrics.py` MUST NOT own benchmark summary formulas.
- `benchmark.py` MUST NOT own strategy metric formulas.
- `visualization.py` MUST NOT become the canonical owner of metric definitions.
- `report.py` MUST NOT recompute metric or benchmark formulas.
- `experiment_runner.py` MUST NOT define formulas inline when an owning module exists.

#### Inputs / outputs / contracts

- Strategy metrics contract:
  - `MetricReport` remains the canonical in-memory summary container for strategy metrics
  - it is produced by `metrics.compute_metrics()`
- Benchmark summary contract:
  - `BenchmarkSummary` is the canonical benchmark summary mapping
  - it contains `total_return` and `max_drawdown`
- Presentation-only contract:
  - drawdown series in figures are display-only derivatives
  - a figure may derive drawdown from an equity curve, but that derivation is not the canonical metric definition

#### Invariants

- Sharpe ratio is only defined canonically in `metrics.py`.
- Strategy max drawdown is only defined canonically in `metrics.py`.
- Benchmark total return and benchmark max drawdown are only defined canonically in `benchmark.py`.
- Visualization may reuse the same numeric ingredients for plotting, but it does not own their business meaning.

#### Cross-module dependencies

- `experiment_runner.py` consumes `metrics.py` and `benchmark.py` outputs.
- `report.py` consumes `BenchmarkSummary` and `MetricReport`.
- `visualization.py` consumes already-computed runtime frames and benchmark curves.
- `scoring.py` MAY consume `MetricReport` for ranking without owning the metrics themselves.

#### Failure modes if this boundary is violated

- Ranking, reporting, and plotting use inconsistent drawdown or return logic.
- Benchmark charts diverge from benchmark summaries.
- A future refactor can silently change formulas in one module without updating the canonical owner.

#### Migration notes from current implementation

- `metrics.py` already owns the strategy metrics formula set.
- `benchmark.py` already owns buy-and-hold curve generation and benchmark summary normalization.
- `visualization.py` already treats drawdown as a figure-building concern; this change freezes that as a non-authoritative derivation.

#### Open questions / deferred decisions

- Whether additional benchmark variants beyond buy-and-hold should be added later is deferred.

### Requirement: Runtime, presentation, and persisted artifact contracts are layered

`src/alphaforge/schemas.py`, `src/alphaforge/report.py`, `src/alphaforge/visualization.py`, `src/alphaforge/storage.py`, `src/alphaforge/experiment_runner.py`, and `src/alphaforge/cli.py` SHALL maintain a three-layer contract stack: canonical runtime contract, enriched presentation contract, and persisted artifact contract.

#### Purpose

- Keep runtime truth, user-facing presentation, and persisted file layouts separate.
- Prevent report, storage, or CLI layers from becoming alternate owners of runtime schemas.

#### Canonical owner

- `src/alphaforge/schemas.py` is the single authoritative owner of in-memory runtime dataclasses and shared type aliases.
- `src/alphaforge/report.py` and `src/alphaforge/visualization.py` are the single authoritative owners of enriched presentation contracts.
- `src/alphaforge/storage.py` is the single authoritative owner of persisted artifact schemas, filenames, and directory layout.
- `src/alphaforge/experiment_runner.py` is orchestration-only and may compose but not redefine these contracts.
- `src/alphaforge/cli.py` is command payload assembly only and may serialize but not redefine these contracts.

#### Allowed responsibilities

- Runtime contract layer MAY define:
  - `DataSpec`
  - `StrategySpec`
  - `BacktestConfig`
  - `TradeRecord`
  - `MetricReport`
  - `ExperimentResult`
  - `ValidationResult`
  - `WalkForwardFoldResult`
  - `WalkForwardResult`
- Presentation contract layer MAY define:
  - `ExperimentReportInput`
  - `SearchReportLinkContext`
  - any figure-only inputs needed to render reports
  - explicit artifact reference bundles used for display
- Persisted artifact layer MAY define:
  - `ArtifactReceipt`
  - JSON payload shapes
  - CSV column layouts
  - filename constants
  - directory layout and path materialization

#### Explicit non-responsibilities

- `schemas.py` MUST NOT own persistence-only path layout, file naming, or report HTML contract.
- `report.py` and `visualization.py` MUST NOT own runtime execution semantics or persistence schema definitions.
- `storage.py` MUST NOT define metric formulas, benchmark formulas, or strategy semantics.
- `experiment_runner.py` MUST NOT become the canonical source of runtime semantics, presentation-specific truth, or persistence schema.
- `cli.py` MUST NOT invent a parallel artifact contract.

#### Inputs / outputs / contracts

- Minimum runtime contract:
  - runtime dataclasses in `schemas.py`
  - backtest output frames and trade records from `backtest.py`
  - strategy metrics from `metrics.py`
  - benchmark summary from `benchmark.py`
- Enriched presentation contract:
  - report inputs and explicit artifact references required to render HTML and CLI user output
- Persisted artifact contract:
  - storage-owned serializations and receipts returned by `storage.py`

#### Invariants

- Runtime dataclasses can exist independently of any persisted artifact path.
- Presentation inputs MUST be explicit; report and visualization code MUST NOT infer storage layout from runtime objects when explicit artifact refs are available.
- Persisted artifact schemas are separate contracts even when some field names overlap runtime dataclasses.
- Save/write functions materialize persisted artifacts without redefining domain truth.

#### Cross-module dependencies

- `experiment_runner.py` composes runtime outputs and presentation inputs from canonical owners.
- `storage.py` consumes runtime objects and produces persisted artifacts and receipts.
- `report.py` consumes explicit presentation inputs and explicit artifact refs.
- `cli.py` serializes runtime, presentation, and persistence outputs without redefining them.

#### Failure modes if this boundary is violated

- Runtime dataclasses accrete persistence-only fields and stop representing pure in-memory truth.
- Reports or CLI payloads start guessing file layouts instead of consuming explicit refs.
- Persisted JSON/CSV shapes drift from runtime truth because serializers and dataclasses are both treated as authorities.
- Later runner decompositions become unsafe because no one can tell which layer owns the contract.

#### Migration notes from current implementation

- `ExperimentReportInput`, `SearchReportLinkContext`, `SearchExecutionOutput`, and `ArtifactReceipt` already act as explicit presentation/persistence inputs.
- This change freezes the runtime contract beneath them so they do not back-propagate schema authority into `schemas.py`.

#### Open questions / deferred decisions

- Whether future report inputs should be split further into per-report input dataclasses is deferred.

### Requirement: `experiment_runner.py`, `storage.py`, and `cli.py` are non-owning layers

`src/alphaforge/experiment_runner.py`, `src/alphaforge/storage.py`, and `src/alphaforge/cli.py` SHALL remain orchestration-only, persistence-only, and command-payload-only respectively.

#### Purpose

- Prevent runner decomposition from being blocked by unresolved contract ownership.
- Keep CLI and storage from becoming implicit owners of runtime rules or presentation truth.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` is the single authoritative owner of workflow sequencing only.
- `src/alphaforge.storage.py` is the single authoritative owner of persistence-only schemas and receipt materialization.
- `src/alphaforge.cli.py` is the single authoritative owner of user-facing payload assembly.

#### Allowed responsibilities

- `experiment_runner.py` MAY:
  - sequence loading, strategy dispatch, backtest execution, metric computation, benchmark preparation, persistence, and report preparation
  - assemble runner-local bundles such as execution outputs or search outputs
  - enforce workflow protocol checks such as fold generation or train/test split rules
- `storage.py` MAY:
  - serialize runtime and validation objects
  - write JSON and CSV artifacts
  - materialize artifact paths and receipts
- `cli.py` MAY:
  - assemble JSON payloads from explicit runtime or persistence outputs
  - omit fields that are not available
  - display report paths returned by explicit report or storage owners

#### Explicit non-responsibilities

- `experiment_runner.py` MUST NOT define metric formulas, benchmark formulas, market-data rules, or storage layout rules.
- `storage.py` MUST NOT redefine runtime result meaning or report rendering meaning.
- `cli.py` MUST NOT infer artifact paths, persistence layout, or report layout.

#### Inputs / outputs / contracts

- Runner inputs:
  - canonical runtime contracts
  - explicit report inputs
  - explicit artifact receipts
- Storage outputs:
  - persisted JSON/CSV artifacts
  - `ArtifactReceipt`
- CLI outputs:
  - command payloads built from explicit serialized inputs

#### Invariants

- The runner may compose, but it does not become a second source of truth.
- Storage may persist, but it does not become a second source of runtime semantics.
- CLI may display, but it does not become a second source of schema or layout truth.

#### Cross-module dependencies

- `experiment_runner.py` depends on runtime, metric, benchmark, report, and storage owners.
- `storage.py` depends on runtime contracts only as serializer input.
- `cli.py` depends on runner outputs and storage/report serializers.

#### Failure modes if this boundary is violated

- Orchestration code becomes a god module that silently owns formulas or layouts.
- Persistence changes break CLI payloads because path truth was guessed in multiple places.
- Future runner decomposition must unwind hidden ownership from downstream layers.

#### Migration notes from current implementation

- Runner-local wrapper types already exist for execution and search outputs.
- CLI search summaries already consume explicit artifact paths instead of inferring them.
- Storage already uses receipt-style persistence outputs.

#### Open questions / deferred decisions

- Whether runner-local wrappers should later be promoted into a narrower application-layer DTO module is deferred.

