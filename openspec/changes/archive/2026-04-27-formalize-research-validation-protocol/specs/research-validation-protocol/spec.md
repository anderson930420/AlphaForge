# research-validation-protocol Specification

## Purpose

Define AlphaForge's formal multi-year strategy research validation protocol: how development-period research, walk-forward validation, permutation diagnostics, freeze gates, and final holdout evaluation are combined without leaking final holdout data into development decisions.

## ADDED Requirements

### Requirement: Multi-year research data is split into development and final holdout periods

AlphaForge MUST define a research protocol that starts from multi-year OHLCV data and splits that data into a development period and a final holdout period before development research begins.

The final holdout period MUST be frozen before strategy development, scoring selection, risk-filter selection, walk-forward validation, permutation diagnostics, or acceptance criteria tuning begins.

#### Scenario: final holdout is frozen before development research

- GIVEN multi-year OHLCV data is selected for a research program
- WHEN the formal research validation protocol begins
- THEN the data MUST be partitioned into a development period and a final holdout period
- AND the final holdout period MUST be declared and frozen before development research starts
- AND the frozen final holdout MUST NOT be inspected to choose strategy parameters, scoring rules, risk filters, or acceptance criteria

### Requirement: Development research uses development data only

Strategy search, parameter search, scoring-rule selection, risk-filter selection, walk-forward validation, and permutation diagnostics MUST use only development-period data until the final holdout evaluation gate is reached.

Final holdout protection is a research protocol boundary and MUST NOT be delegated to individual strategy-family implementations.

#### Scenario: development-only research workflows

- GIVEN the final holdout period has been frozen
- WHEN AlphaForge runs strategy family exploration, parameter search, scoring-rule selection, risk-filter selection, walk-forward validation, or permutation diagnostics
- THEN those workflows MUST receive only development-period data
- AND they MUST NOT consume final holdout rows
- AND strategy-family code MUST NOT be responsible for enforcing final holdout access protection

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

Before touching the final holdout, AlphaForge MUST freeze the strategy family, parameter selection rule, scoring formula, transaction cost assumptions, risk filters, report format, and acceptance criteria.

The freeze gate MUST occur after development-period research evidence is complete and before final holdout evaluation starts.

#### Scenario: final holdout gate requires a frozen research plan

- GIVEN development-period search, walk-forward validation, and diagnostics are complete
- WHEN AlphaForge prepares to evaluate the final holdout
- THEN the strategy family MUST be frozen
- AND the parameter selection rule MUST be frozen
- AND the scoring formula MUST be frozen
- AND transaction cost assumptions MUST be frozen
- AND risk filters MUST be frozen
- AND report format MUST be frozen
- AND acceptance criteria MUST be frozen
- AND the final holdout MUST NOT be evaluated until the freeze gate is satisfied

### Requirement: Final holdout is evaluated once for research decisions and never used for tuning

Final holdout evaluation MUST be limited to one research-decision evaluation after the pre-holdout freeze gate is satisfied.

Deterministic reruns of the same frozen plan MAY be allowed only for reproducibility, audit, or artifact regeneration, provided that the rerun does not alter strategy parameters, parameter selection rules, scoring formulas, transaction cost assumptions, risk filters, report format, acceptance criteria, or candidate promotion decisions.

Final holdout results MUST NOT be used to tune strategy parameters, parameter selection rules, scoring formulas, transaction cost assumptions, risk filters, report format, or acceptance criteria.

#### Scenario: one-time final holdout evaluation

- GIVEN the pre-holdout freeze gate is satisfied
- WHEN AlphaForge evaluates the final holdout
- THEN the research-decision evaluation MUST occur only once
- AND the selected strategy and frozen decision rules MUST be applied without further development changes
- AND final holdout results MUST NOT feed back into parameter tuning, scoring-rule changes, risk-filter changes, report-format changes, or acceptance-criteria changes

#### Scenario: deterministic rerun does not create a new research decision

- GIVEN the final holdout has already been evaluated for the frozen research plan
- WHEN AlphaForge reruns the same final holdout evaluation for reproducibility, audit, or artifact regeneration
- THEN the rerun MAY be allowed
- AND the rerun MUST use the same frozen strategy parameters, parameter selection rules, scoring formulas, transaction cost assumptions, risk filters, report format, and acceptance criteria
- AND the rerun MUST NOT alter candidate promotion decisions
- AND the rerun MUST NOT create a new tuning loop

#### Scenario: failed final holdout does not reopen development tuning

- GIVEN the final holdout result fails the frozen acceptance criteria
- WHEN the result is reviewed
- THEN AlphaForge MUST NOT tune the same research run using final holdout feedback
- AND any later research attempt MUST be treated as a new research program with a newly declared development/holdout protocol

### Requirement: Final reports disclose research process evidence and search breadth

Final reports produced for a protocol-governed research program MUST disclose the development search space size, number of tried strategy families, number of tried parameter combinations, walk-forward out-of-sample summary, train/test degradation, permutation diagnostic result, transaction cost assumptions, final holdout result, and rejected or failed candidate summary when available.

This requirement defines disclosure obligations only. It MUST NOT own report rendering implementation, storage layout, file naming, or presentation formatting.

#### Scenario: final report contains required protocol disclosures

- GIVEN a final report is produced after final holdout evaluation
- WHEN the report describes the protocol-governed research program
- THEN it MUST disclose development search space size
- AND it MUST disclose the number of tried strategy families
- AND it MUST disclose the number of tried parameter combinations
- AND it MUST disclose the walk-forward out-of-sample summary
- AND it MUST disclose train/test degradation
- AND it MUST disclose the permutation diagnostic result
- AND it MUST disclose transaction cost assumptions
- AND it MUST disclose the final holdout result
- AND it MUST disclose rejected or failed candidate summary when available

### Requirement: Protocol scope excludes lower-level execution, data, strategy, storage, CLI, and rendering ownership

The research validation protocol MUST coordinate existing search, walk-forward, permutation, policy, comparison, and reporting concepts at the research-process level only.

The protocol MUST NOT redefine core backtest execution semantics, market data schema, strategy signal generation, artifact persistence layout, CLI formatting, or report-rendering implementation details.

#### Scenario: lower-level boundaries remain authoritative

- GIVEN a workflow is governed by the research validation protocol
- WHEN it runs backtests, loads market data, generates strategy signals, persists artifacts, parses CLI options, or renders reports
- THEN the existing owner for each lower-level boundary remains authoritative
- AND the research validation protocol MUST NOT duplicate or override those lower-level contracts
