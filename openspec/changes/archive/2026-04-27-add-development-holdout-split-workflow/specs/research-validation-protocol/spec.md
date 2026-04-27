# research-validation-protocol Specification

## MODIFIED Requirements

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
