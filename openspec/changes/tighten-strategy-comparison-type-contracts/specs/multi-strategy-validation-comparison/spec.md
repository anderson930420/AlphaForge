# multi-strategy-validation-comparison Specification

## Purpose

Define the type-contract tightening for comparison verdict domains and strategy-family parameter grids.

## MODIFIED Requirements

### Requirement: Comparison summary contract

AlphaForge SHALL produce a runtime comparison summary and persisted `comparison_summary.json`.

The summary SHALL include:

- `data_spec`
- `split_config`
- `backtest_config`
- `strategy_families`
- `permutation_config`
- `research_policy_config`
- `comparison_results`
- `artifact_paths`
- `metadata`

#### Scenario: summary contains one result per family

- GIVEN a comparison request contains two strategy families
- WHEN the workflow completes
- THEN the summary SHALL contain two comparison results
- AND each result SHALL expose its selected parameters, train/test scores, test metrics, permutation status, and research-policy verdict

#### Scenario: comparison preserves distinct verdict domains

- GIVEN a strategy comparison result contains both policy verdict fields
- WHEN the result is constructed, serialized, or ranked
- THEN `research_policy_verdict` SHALL use only the research policy domain `promote`, `reject`, or `blocked`
- AND `candidate_policy_verdict` SHALL use only the candidate policy domain `candidate`, `validated`, `rejected`, or `inconclusive`
- AND AlphaForge SHALL NOT substitute either verdict system for the other

### Requirement: Comparison result ranking contract

AlphaForge SHALL keep research-policy verdicts visible and SHALL NOT promote rejected candidates at comparison level.

#### Scenario: comparison ranking is advisory

- GIVEN comparison results have research-policy verdicts
- WHEN results are ordered
- THEN `promote` results SHALL sort before `blocked` results
- AND `blocked` results SHALL sort before `reject` results
- AND each group SHALL sort by descending test score
- AND the original per-candidate verdict SHALL remain visible

#### Scenario: ranking consumes research-policy verdicts only

- GIVEN comparison results also expose candidate policy verdicts
- WHEN comparison ranking groups results by policy outcome
- THEN the grouping SHALL use `research_policy_verdict`
- AND candidate policy verdicts SHALL remain reporting evidence rather than comparison-level promotion authority

### Requirement: Supported strategy-family configuration contract

AlphaForge SHALL support comparison search configs for `ma_crossover` and `breakout`.

Parameter grids SHALL be numeric-only for now and SHALL allow `int` and `float` values.
Categorical, string, and boolean search parameters are intentionally out of scope.

#### Scenario: MA crossover config

- GIVEN a comparison includes `ma_crossover`
- WHEN the family search config is built
- THEN it SHALL contain `short_window` and `long_window` parameter grids

#### Scenario: breakout config

- GIVEN a comparison includes `breakout`
- WHEN the family search config is built
- THEN it SHALL contain a `lookback_window` parameter grid

#### Scenario: numeric parameter grid contract

- GIVEN a strategy-family search config is constructed
- WHEN it declares a parameter grid
- THEN each parameter value SHALL be typed as `int | float`
- AND existing integer window grids SHALL remain valid
- AND future numeric float thresholds or decay values SHALL be representable at the schema/type-contract level

#### Scenario: unsupported family

- GIVEN a comparison includes an unsupported strategy family
- WHEN request validation or workflow execution occurs
- THEN AlphaForge SHALL fail clearly
- AND it SHALL NOT silently skip the family

### Requirement: Failure and partial-result behavior

The MVP comparison workflow SHALL fail fast.

Parallel strategy comparison execution is intentionally out of scope.

#### Scenario: family validation fails

- GIVEN one supported strategy family fails validation or has no train search result
- WHEN the comparison workflow executes
- THEN the whole comparison run SHALL fail clearly
- AND AlphaForge SHALL NOT emit a misleading row with fake metrics

#### Scenario: parallel execution is deferred

- GIVEN multiple strategy families are included
- WHEN comparison runs
- THEN AlphaForge SHALL execute using the existing serial workflow
- AND it SHALL NOT introduce parallel execution until artifact-write safety, logging behavior, and partial failure semantics are specified

## Open questions / deferred decisions

- Strategy comparison may later support parallel execution, but only after artifact-write safety, logging behavior, and partial failure semantics are specified.
