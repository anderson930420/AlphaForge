# research-validation-protocol Specification

## Purpose
TBD - created by archiving change formalize-research-validation-protocol. Update Purpose after archive.
## Requirements
### Requirement: Multi-year research data is split into development and final holdout periods

AlphaForge MUST provide a runtime research validation workflow that loads canonical multi-year OHLCV data and splits it into explicit development and final holdout periods before any protocol-governed research evidence is generated.

The split MUST use datetime period boundaries supplied by the request. Development and holdout rows MUST be non-empty, disjoint, and chronological for normal research use, with the final holdout period occurring after the development period.

#### Scenario: runtime split returns disjoint development and holdout data

- GIVEN canonical OHLCV data contains rows inside both requested periods
- WHEN the research validation workflow splits the data
- THEN the development frame MUST contain only rows inside the requested development period
- AND the final holdout frame MUST contain only rows inside the requested holdout period
- AND both frames MUST be non-empty
- AND the development and final holdout datetime values MUST be disjoint

#### Scenario: overlapping or non-chronological periods are rejected

- GIVEN requested development and final holdout date ranges overlap
- OR the final holdout starts at or before the development period ends
- WHEN the research validation workflow validates the split
- THEN AlphaForge MUST reject the request before running search, walk-forward validation, permutation diagnostics, final holdout evaluation, or artifact persistence

### Requirement: Development research uses development data only

The runtime research validation workflow MUST run development-period search, development-period walk-forward validation, scoring-based candidate selection, and optional permutation diagnostics using only the development frame produced by the protocol split.

The workflow MUST select the final candidate from development-period evidence only.

#### Scenario: development evidence excludes holdout rows

- GIVEN the research validation workflow has split development and final holdout frames
- WHEN it runs search, walk-forward validation, or optional permutation diagnostics
- THEN those development evidence workflows MUST receive only development-frame rows
- AND they MUST NOT receive final holdout rows
- AND candidate selection MUST be based only on development-period search evidence

### Requirement: Walk-forward validation produces multiple development-period OOS folds

Walk-forward validation under the research protocol MUST produce multiple out-of-sample folds entirely inside the development period.

Walk-forward evidence MUST be treated as development-period out-of-sample evidence and MUST NOT be represented as final holdout evidence.

#### Scenario: walk-forward OOS remains inside development

- GIVEN development data has been separated from final holdout data
- WHEN walk-forward validation runs under the research protocol
- THEN it MUST create multiple out-of-sample folds within the development period
- AND every training fold and out-of-sample fold MUST be contained inside the development period
- AND no walk-forward fold MUST include final holdout rows
- AND the resulting walk-forward summary MUST be labeled or represented as development-period evidence rather than final holdout evidence

### Requirement: Permutation diagnostics are robustness diagnostics, not standalone profitability proof

Permutation diagnostics SHOULD be used as robustness diagnostics for candidate evidence and MUST NOT be treated as standalone proof that a strategy is profitable.

Permutation diagnostics under this protocol SHOULD prefer block permutation or block shuffle over naive independent row shuffling because financial time series may contain local autocorrelation, volatility clustering, and regime structure.

#### Scenario: permutation result is diagnostic evidence

- GIVEN a candidate has development-period validation evidence
- WHEN permutation diagnostics are run for the candidate
- THEN the permutation result MUST be represented as robustness diagnostic evidence
- AND the permutation result MUST NOT by itself prove profitability
- AND policy, comparison, or reporting layers MUST NOT promote a candidate solely because its permutation diagnostic passes

#### Scenario: block permutation is preferred for financial time series

- GIVEN permutation diagnostics are configured for protocol-level research evidence
- WHEN the null construction method is selected
- THEN AlphaForge SHOULD prefer block permutation or block shuffle over naive independent row shuffling
- AND the rationale SHOULD preserve local autocorrelation, volatility clustering, and regime structure better than independent row shuffling

### Requirement: Pre-holdout decisions are frozen before final holdout evaluation

The runtime research validation workflow MUST freeze the selected candidate and protocol plan before final holdout evaluation begins.

The frozen plan MUST include strategy family, selected parameters, parameter selection rule, scoring formula name, transaction cost assumptions, development period, holdout period, search space size, tried strategy families, tried parameter combinations, walk-forward configuration, and permutation configuration when enabled.

#### Scenario: frozen plan is recorded before holdout evaluation

- GIVEN development-period search and walk-forward evidence have completed
- WHEN the workflow prepares final holdout evaluation
- THEN it MUST record the frozen selected strategy family and selected parameters
- AND it MUST record the selection rule and scoring formula name used for development selection
- AND it MUST record transaction cost assumptions, periods, search breadth, walk-forward configuration, and permutation configuration when available
- AND final holdout evaluation MUST use the frozen selected candidate without rerunning parameter search on holdout data

### Requirement: Final holdout is evaluated once for research decisions and never used for tuning

The runtime research validation workflow MUST evaluate final holdout data using only the frozen selected candidate and frozen plan.

Final holdout results MUST NOT alter selected parameters, parameter selection rules, scoring formulas, transaction cost assumptions, risk filters, report format, acceptance criteria, or candidate promotion decisions.

#### Scenario: holdout result does not affect candidate selection

- GIVEN the workflow has frozen a selected candidate from development evidence
- WHEN it evaluates the final holdout
- THEN it MUST evaluate only that frozen candidate on holdout data
- AND it MUST NOT run parameter search on holdout data
- AND it MUST NOT change selected parameters or selection rules based on holdout metrics
- AND it MUST expose holdout metrics separately from development evidence

### Requirement: Final reports disclose research process evidence and search breadth

The runtime research validation workflow MUST produce or expose a protocol summary that clearly separates development evidence, walk-forward development-period out-of-sample evidence, optional permutation diagnostic evidence, frozen plan, and final holdout result.

The summary MUST include development and holdout periods, row counts, selected strategy, selected parameters, selection rule, search breadth, walk-forward summary, optional permutation summary, final holdout metrics, and transaction cost assumptions.

#### Scenario: protocol summary labels development OOS and final holdout separately

- GIVEN the research validation workflow completes
- WHEN the protocol summary is returned or persisted
- THEN walk-forward evidence MUST be labeled as development-period OOS evidence
- AND final holdout metrics MUST be labeled as final holdout evidence
- AND the summary MUST include search-space size, tried strategy family count, tried parameter combination count, transaction cost assumptions, frozen plan, and artifact references when persisted

### Requirement: Protocol scope excludes lower-level execution, data, strategy, storage, CLI, and rendering ownership

The runtime research validation workflow MUST coordinate existing data loading, search, walk-forward, permutation, final candidate evaluation, and storage concepts without redefining lower-level ownership.

#### Scenario: workflow delegates lower-level semantics

- GIVEN the research validation workflow runs
- WHEN it loads data, executes backtests, generates strategy signals, computes metrics, persists artifacts, parses CLI arguments, or renders reports
- THEN it MUST delegate to the existing canonical owners for those concerns
- AND it MUST NOT modify backtest execution semantics
- AND it MUST NOT redefine market data schema or strategy signal generation
- AND it MUST NOT implement report rendering
- AND it MUST NOT put storage-owned artifact schema in CLI code

### Requirement: External signal-backed custom-signal validation is protocol-owned and file-driven

The runtime research validation workflow MUST support a `custom_signal` path that validates an external `signal.csv` file before final candidate evaluation.

The workflow MUST delegate signal-file validation and target-position derivation to the custom-signal boundary and MUST NOT compute signal values internally.

#### Scenario: custom-signal workflow consumes external signals without generating them

- GIVEN a caller runs `alphaforge research-validate --strategy custom_signal --signal-file ...`
- WHEN the workflow prepares the candidate
- THEN AlphaForge MUST validate the external signal file through the custom-signal boundary
- AND it MUST derive target positions from `signal_binary`
- AND it MUST ignore `signal_value` for execution
- AND it MUST NOT import SignalForge internals

#### Scenario: signal dates are aligned with market data before evidence generation

- GIVEN the workflow has accepted market data and an external signal file
- WHEN the workflow validates `custom_signal`
- THEN signal dates MUST align with the market-data dates
- AND duplicate `datetime` values for the same `symbol` MUST fail
- AND missing signal dates MUST fail by default
- AND `available_at` MUST be less than or equal to `datetime`

### Requirement: `research-validate` accepts a custom-signal input contract without owning it

The workflow MAY accept an external signal-file path for `custom_signal`, but the signal-file contract itself MUST remain owned by the custom-signal boundary.

#### Scenario: workflow accepts the signal file path and defers validation

- GIVEN the CLI or a programmatic caller supplies a signal-file path
- WHEN the workflow enters the custom-signal branch
- THEN the workflow SHALL pass the path to the custom-signal boundary
- AND it SHALL NOT inspect file contents beyond orchestration needs

### Requirement: research validation always emits minimal evidence diagnostics

The runtime research validation workflow SHALL emit cost-sensitivity diagnostics and bootstrap evidence diagnostics for the selected candidate using documented default diagnostic parameters.

The workflow SHALL remain research-validation oriented and SHALL NOT add PBO, DSR, White Reality Check, Hansen SPA, full TCA, broker execution simulation, or limit-order-book simulation.

#### Scenario: diagnostics are emitted by default

- GIVEN a valid research-validation request
- WHEN the workflow evaluates the selected candidate
- THEN it SHALL compute cost sensitivity diagnostics
- AND it SHALL compute bootstrap evidence diagnostics
- AND it SHALL include those diagnostics in the research-validation outputs by default

#### Scenario: advanced diagnostics remain out of scope

- GIVEN the workflow runs with minimal diagnostics enabled
- WHEN the outputs are assembled
- THEN the workflow SHALL NOT claim to implement PBO, DSR, White Reality Check, Hansen SPA, or a full execution simulator

### Requirement: research protocol summary exposes diagnostics alongside evidence and holdout results

`research_protocol_summary.json` SHALL include the minimal evidence diagnostics for the selected candidate alongside the existing development evidence and final holdout result.

The summary SHALL expose:

- the selected candidate evidence
- the cost-sensitivity diagnostic
- the bootstrap evidence diagnostic
- the final holdout result

#### Scenario: protocol summary includes evidence diagnostics

- GIVEN the research-validation workflow completes
- WHEN the protocol summary is persisted or returned
- THEN the summary SHALL contain cost sensitivity and bootstrap evidence
- AND the diagnostics SHALL be clearly associated with the selected candidate

### Requirement: research validation delegates diagnostics to a focused diagnostics module

`runner_workflows.py` SHALL orchestrate diagnostics generation but SHALL NOT own diagnostic formulas.

The diagnostic formulas and resampling / scenario logic SHALL be owned by a focused module such as `src/alphaforge/evidence_diagnostics.py`.

#### Scenario: workflow orchestration remains thin

- GIVEN a research-validation run needs diagnostics
- WHEN the workflow executes
- THEN it SHALL delegate diagnostics to the focused diagnostics owner
- AND it SHALL NOT reimplement cost-sensitivity or bootstrap formulas inside orchestration code

