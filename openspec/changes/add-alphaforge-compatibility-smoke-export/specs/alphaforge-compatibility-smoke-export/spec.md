## ADDED Requirements

### Requirement: SignalForge exports a deterministic AlphaForge compatibility smoke package

SignalForge SHALL provide a deterministic compatibility smoke export package that bundles an AlphaForge-compatible market-data CSV together with the matching SignalForge signal artifacts and package metadata.

The package SHALL be written under `examples/alphaforge_compatibility/<symbol>_<start>_<end>/` and SHALL include:
- `market_data.csv`
- `signal.csv`
- `signal_contract.yaml`
- `data_quality_report.json`
- `manifest.json`
- `README.md`

#### Scenario: smoke package layout is complete

- **WHEN** the compatibility smoke export helper runs
- **THEN** it SHALL create the package directory
- **AND** it SHALL write all six required files
- **AND** it SHALL NOT require AlphaForge to generate or validate the package

### Requirement: `market_data.csv` is AlphaForge-compatible OHLCV input

The smoke package SHALL include a canonical AlphaForge-compatible OHLCV market-data CSV with exactly these columns in stable order:
`datetime`, `open`, `high`, `low`, `close`, `volume`.

The datetime set in `market_data.csv` SHALL exactly match the datetime set in `signal.csv`.

#### Scenario: market data aligns with the signal bundle

- **WHEN** the smoke package is exported
- **THEN** `market_data.csv` SHALL contain only AlphaForge-compatible OHLCV columns
- **AND** every market-data datetime SHALL align exactly with a `signal.csv` datetime
- **AND** the package SHALL NOT include extra market-data dates that would break the AlphaForge custom_signal smoke test

### Requirement: `signal.csv` remains AlphaForge-compatible and execution-safe

The smoke package SHALL include a `signal.csv` with exactly these columns in stable order:
`datetime`, `available_at`, `symbol`, `signal_name`, `signal_value`, `signal_binary`, `source`.

`signal_binary` SHALL contain only `0` or `1`, `available_at` SHALL be less than or equal to `datetime`, and the package SHALL not contain duplicate `(datetime, symbol, signal_name)` rows.

The package SHALL preserve `signal_value` in the artifact but SHALL NOT require SignalForge to use `signal_value` for downstream AlphaForge execution.

#### Scenario: signal bundle is consumable by AlphaForge custom_signal

- **WHEN** the smoke package is consumed by AlphaForge
- **THEN** `signal.csv` SHALL satisfy the AlphaForge custom_signal contract
- **AND** `signal_value` SHALL remain present only as a schema field
- **AND** the package SHALL not depend on AlphaForge internals

### Requirement: `signal_contract.yaml` provides package-level compatibility summary

The smoke package `signal_contract.yaml` SHALL include the core signal contract metadata and a package-level compatibility summary with:
- `signal_name`
- `source`
- `factor`
- `factor_params`
- `decision_rule`
- `timing_rule`
- `schema_version`
- `output_file`
- `row_count`
- `symbol`
- `datetime_start`
- `datetime_end`
- `generator`

`row_count` SHALL refer to emitted signal rows for the compatibility package.

#### Scenario: contract summarizes the smoke package

- **WHEN** `signal_contract.yaml` is written for the smoke package
- **THEN** it SHALL summarize the exported signal bundle
- **AND** `row_count` SHALL equal the number of rows in `signal.csv`
- **AND** `generator` SHALL be `SignalForge`

### Requirement: `data_quality_report.json` summarizes the smoke package signal bundle

The smoke package `data_quality_report.json` SHALL summarize the exported signal bundle using:
- `source_type`
- `symbol_count`
- `row_count`
- `start_date`
- `end_date`
- `duplicate_rows`
- `missing_values`
- `warnings`
- `generator`

For this compatibility package, `row_count` SHALL refer to emitted signal rows.

#### Scenario: quality report summarizes exported signal rows

- **WHEN** `data_quality_report.json` is written for the smoke package
- **THEN** `row_count` SHALL equal the number of rows in `signal.csv`
- **AND** `generator` SHALL be `SignalForge`
- **AND** the report SHALL remain a SignalForge artifact, not an AlphaForge artifact

### Requirement: `manifest.json` records the smoke package contract and file integrity

The smoke package SHALL include a `manifest.json` with at least:
- `package_name`
- `package_version`
- `generator`
- `generated_for`
- `symbol`
- `start_date`
- `end_date`
- `market_data_file`
- `signal_file`
- `signal_contract_file`
- `data_quality_report_file`
- `row_count`
- `schema_version`
- `alpha_forge_strategy`
- `expected_alpha_forge_execution_semantics`

The manifest MAY include sha256 hashes for package files when easy to compute.

#### Scenario: manifest makes the AlphaForge handoff explicit

- **WHEN** the smoke package is exported
- **THEN** `manifest.json` SHALL identify the package as a SignalForge export for AlphaForge consumption
- **AND** it SHALL record the expected AlphaForge strategy as `custom_signal`
- **AND** it SHALL record the expected AlphaForge execution semantics as `legacy_close_to_close_lagged`

### Requirement: Package README documents the AlphaForge handoff

The smoke package SHALL include a `README.md` that explains:
- what the package is
- that SignalForge generated the signal
- that AlphaForge should validate and backtest the package only
- that AlphaForge must not import SignalForge internals
- the exact `alphaforge research-validate --strategy custom_signal --signal-file ...` command using paths inside the package
- that `signal_binary` maps to `target_position`
- that `signal_value` is not computed or used by AlphaForge
- that the expected execution semantics are `legacy_close_to_close_lagged`

#### Scenario: package README provides the smoke-test command

- **WHEN** a user opens the package README
- **THEN** it SHALL show the exact AlphaForge smoke-test command
- **AND** it SHALL reference both `market_data.csv` and `signal.csv`
- **AND** it SHALL clearly state the SignalForge/AlphaForge handoff boundary

### Requirement: Compatibility smoke export is deterministic and SignalForge-only

Repeated exports with the same input data and package metadata SHALL produce byte-for-byte identical package files.

SignalForge SHALL NOT import AlphaForge or add AlphaForge as a dependency to satisfy this export.

#### Scenario: identical inputs yield identical package files

- **WHEN** the compatibility smoke export helper is run twice with the same inputs
- **THEN** the package files SHALL be byte-for-byte identical
- **AND** the implementation SHALL not require AlphaForge imports or dependencies
