# Delta for Storage Artifact Ownership

## ADDED Requirements

### Requirement: `trade_log.csv` is a return-based public artifact schema

`src/alphaforge/storage.py` SHALL own the persisted `trade_log.csv` schema and SHALL persist the return-based trade-log fields emitted by `backtest.py`.

#### Purpose

- Keep the public artifact contract aligned with the return-based trade semantics.
- Prevent the persisted trade log from drifting back into dollar-PnL terminology.

#### Canonical owner

- `src/alphaforge/storage.py` is the authoritative owner of the persisted `trade_log.csv` schema.
- `src/alphaforge/backtest.py` is the authoritative owner of the runtime trade-return semantics that feed the persisted schema.
- `src/alphaforge/report.py` and `src/alphaforge/cli.py` are downstream presentation consumers only.

#### Allowed responsibilities

- `storage.py` MAY persist the canonical trade-log columns:
  - `entry_datetime`
  - `exit_datetime`
  - `entry_price`
  - `exit_price`
  - `holding_period`
  - `trade_gross_return`
  - `trade_net_return`
  - `cost_return_contribution`
  - `entry_target_position`
  - `exit_target_position`
- `storage.py` MAY include schema-version or compatibility metadata for the migration.
- `storage.py` MAY serialize the execution-semantics metadata and data-quality summary alongside other persisted artifacts as storage-owned JSON payloads.

#### Explicit non-responsibilities

- `storage.py` MUST NOT persist the canonical trade log under PnL-shaped field names.
- `storage.py` MUST NOT redefine trade semantics or win-rate semantics.
- `storage.py` MUST NOT treat report wording as a substitute for artifact schema ownership.
- `report.py` and `cli.py` MUST NOT guess the artifact schema from runtime behavior.

#### Inputs / outputs / contracts

- Inputs:
  - the return-based trade log from `backtest.py`
  - execution metadata emitted by `backtest.py`
  - data-quality summary metadata emitted by `data_loader.py`
- Outputs:
  - `trade_log.csv`
  - any storage-owned schema metadata that documents the migration
- Contract rules:
  - persisted trade-log columns must match the return-based contract
  - the public artifact schema is changed intentionally and must be treated as a breaking schema migration unless compatibility metadata is added explicitly

#### Invariants

- The persisted trade log stays return-based.
- PnL-shaped field names are not part of the canonical schema.
- Storage remains the single source of truth for filenames and CSV column layout.

#### Cross-module dependencies

- `backtest.py` provides the runtime trade log.
- `metrics.py` consumes the persisted schema indirectly through the runtime trade fields.
- `report.py` may render the artifact, but it must not rename or reinterpret the persisted fields.
- `cli.py` may display artifact locations, but it must not infer alternate schemas.

#### Failure modes if this boundary is violated

- Old and new trade semantics can be serialized side by side without a canonical owner.
- Reports and research summaries can start labeling return contributions as PnL again.
- Public CSV consumers can break if the schema changes without a coordinated migration.

#### Migration notes from current implementation

- The current persisted trade-log shape uses legacy PnL-shaped labels.
- This change requires a single coordinated rename to the return-based schema rather than a long-lived dual schema.
- If a temporary compatibility reader is added, it must be legacy-only and must not become the canonical output contract.

#### Open questions / deferred decisions

- Whether a legacy reader should remain available for historical artifacts is deferred.
  - Recommended default: preserve the new canonical schema in `trade_log.csv` and update downstream tests, fixtures, and report labels in the same controlled migration.

#### Scenario: persisted trade log matches the return-based runtime contract

- GIVEN a backtest result has been persisted
- WHEN `trade_log.csv` is written
- THEN the CSV SHALL contain the return-based trade columns listed above
- AND it SHALL NOT use PnL-shaped canonical field names
