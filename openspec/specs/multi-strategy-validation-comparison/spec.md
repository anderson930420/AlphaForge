# multi-strategy-validation-comparison Specification

## Purpose
TBD - created by archiving change add-multi-strategy-validation-comparison. Update Purpose after archive.
## Requirements
### Requirement: Multi-strategy comparison input contract

AlphaForge SHALL provide a runtime comparison request contract that identifies the shared dataset, split configuration, backtest configuration, strategy-family search configurations, optional permutation configuration, optional research-policy configuration, threshold filters, and output location.

#### Scenario: one comparison run shares one protocol

- GIVEN a comparison request contains multiple strategy families
- WHEN the workflow executes
- THEN all families SHALL use the same `DataSpec`
- AND all families SHALL use the same split ratio
- AND all families SHALL use the same backtest configuration
- AND all families SHALL use the same scoring function
- AND all families SHALL use the same research-policy configuration
- AND all families SHALL use the same permutation configuration when permutation evidence is enabled

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

### Requirement: Per-strategy validation result contract

For each supported strategy family in a comparison, AlphaForge SHALL run the equivalent of `validate-search` for that family and collect the selected candidate evidence.

#### Scenario: per-family best candidate is selected before comparison

- GIVEN `ma_crossover` and `breakout` are compared
- WHEN validation runs
- THEN each family SHALL select its own best train candidate using the existing search/scoring logic
- AND each selected candidate SHALL be rerun on the test split
- AND comparison SHALL compare one selected candidate per family rather than every raw parameter row across all families

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

### Requirement: Artifact layout

AlphaForge SHALL persist comparison artifacts under the comparison output root.

Required top-level artifacts:

- `comparison_summary.json`
- `comparison_results.csv`

Per-family validation artifacts SHALL be placed under:

- `strategies/<strategy_name>/validation_summary.json`
- `strategies/<strategy_name>/train_ranked_results.csv`
- `strategies/<strategy_name>/policy_decision.json`
- `strategies/<strategy_name>/train_best/`
- `strategies/<strategy_name>/test_selected/`
- `strategies/<strategy_name>/permutation_test/` when permutation evidence is enabled and persisted

#### Scenario: family paths do not collide

- GIVEN multiple strategy families are compared
- WHEN artifacts are persisted
- THEN each family SHALL write validation artifacts under its own strategy directory
- AND comparison-level artifacts SHALL be written only at the comparison root

### Requirement: CLI discovery and output contract

AlphaForge SHALL expose a `compare-strategies` CLI command.

The command SHALL accept:

- `--data`
- `--output-dir`
- `--initial-capital`
- `--fee-rate`
- `--slippage-rate`
- `--annualization-factor`
- `--split-ratio`
- `--strategies`
- `--short-windows`
- `--long-windows`
- `--lookback-windows`
- `--permutation-test`
- `--permutations`
- `--permutation-seed`
- `--permutation-block-size`
- `--permutation-null-model`
- `--permutation-scope`

#### Scenario: default strategy selection

- GIVEN `--strategies` is omitted
- WHEN the CLI assembles the comparison request
- THEN it SHALL include `ma_crossover` and `breakout`

#### Scenario: CLI remains a request boundary

- GIVEN the CLI dispatches `compare-strategies`
- WHEN the command runs
- THEN CLI code SHALL assemble request/config objects and call the workflow layer
- AND it SHALL NOT compute metrics, permutation evidence, scoring, or research-policy decisions directly

### Requirement: Permutation evidence behavior

AlphaForge SHALL preserve validation permutation semantics per selected family candidate.

#### Scenario: permutation disabled

- GIVEN comparison runs without `--permutation-test`
- WHEN each family result is collected
- THEN each family SHALL record permutation status as `skipped`
- AND skipped permutation evidence SHALL NOT be represented as passed evidence

#### Scenario: permutation enabled

- GIVEN comparison runs with `--permutation-test`
- WHEN each selected family candidate is evaluated
- THEN each selected candidate SHALL run permutation evidence using its own strategy family and selected parameters
- AND each permutation summary SHALL be passed into research policy
- AND high p-values SHALL be able to reject that candidate
- AND low p-values SHALL be able to pass if all other policy checks pass

### Requirement: Research-policy decision behavior

AlphaForge SHALL run the existing research policy independently for each strategy family candidate.

#### Scenario: per-family policy decisions remain authoritative

- GIVEN one strategy candidate is rejected by research policy
- WHEN comparison results are produced
- THEN the comparison summary SHALL expose the rejection
- AND comparison ranking SHALL NOT convert that candidate into a promoted candidate
- AND no new research-policy verdict vocabulary SHALL be introduced

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

