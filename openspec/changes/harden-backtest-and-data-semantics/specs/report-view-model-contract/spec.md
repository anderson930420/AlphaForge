# Delta for Report View-Model Contract

## ADDED Requirements

### Requirement: report wording preserves return-based trade semantics

`src/alphaforge/report.py` SHALL render trade-related labels using return-based terminology and SHALL NOT relabel the canonical trade contract as dollar PnL.

#### Purpose

- Keep display wording aligned with the return-based artifact and metric contracts.
- Prevent report text from undoing the semantics hardening performed in backtest, metrics, and storage.

#### Canonical owner

- `src/alphaforge/report.py` is the authoritative owner of display wording only.
- `src/alphaforge/storage.py` remains the authoritative owner of the artifact schema being displayed.
- `src/alphaforge/backtest.py` remains the authoritative owner of trade semantics.

#### Allowed responsibilities

- `report.py` MAY display `trade_gross_return`, `trade_net_return`, `cost_return_contribution`, and `holding_period` using human-friendly labels.
- `report.py` MAY display the execution-semantics metadata string `legacy_close_to_close_lagged`.
- `report.py` MAY format percentages and bar counts for presentation.

#### Explicit non-responsibilities

- `report.py` MUST NOT rename return-based trade fields into dollar-PnL language.
- `report.py` MUST NOT imply shares-level accounting, partial fills, or broker-like execution.
- `report.py` MUST NOT recompute trade returns or win rate from raw market data.
- `report.py` MUST NOT infer alternate semantics from artifact names alone.

#### Inputs / outputs / contracts

- Inputs:
  - the return-based trade log from storage or runtime result objects
  - execution-semantics metadata from the backtest contract
  - computed metrics from `metrics.py`
- Outputs:
  - human-readable report labels and sections
- Contract rules:
  - user-facing labels may be friendlier than field names, but they must preserve the return-based meaning
  - report wording must stay consistent with the storage-owned `trade_log.csv` schema

#### Invariants

- Report wording stays downstream of the canonical field names.
- Return-based trade fields are not translated into dollar accounting terms.
- Report rendering does not become a second semantics owner.

#### Cross-module dependencies

- `storage.py` supplies the canonical persisted fields.
- `backtest.py` supplies the canonical semantics.
- `metrics.py` supplies computed metric values such as win rate.
- `cli.py` may print report paths or summaries, but it must not invent alternate wording.

#### Failure modes if this boundary is violated

- The report can say "PnL" while the storage schema and runtime contract say "return", which makes the artifact set internally inconsistent.
- Users can misread the report as showing dollar accounting.
- Legacy wording can survive even after the persisted schema is hardened.

#### Migration notes from current implementation

- The current report layer already renders presentation text from upstream inputs.
- This change requires those labels to move with the new return-based trade schema in the same controlled migration.

#### Open questions / deferred decisions

- None for display wording.

#### Scenario: reports render return-based trade labels

- GIVEN a report renders trade details from the persisted trade log
- WHEN it displays the trade fields
- THEN it SHALL preserve return-based terminology
- AND it SHALL NOT relabel the canonical trade contract as dollar PnL
