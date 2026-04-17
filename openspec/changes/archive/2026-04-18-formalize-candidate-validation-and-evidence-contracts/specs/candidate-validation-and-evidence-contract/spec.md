# Delta for Candidate Validation and Evidence Contract

## ADDED Requirements

### Requirement: validation flows expose a canonical candidate-evidence summary

`validate-search` SHALL produce a canonical candidate-evidence summary for the searched candidate it evaluates on the train/test split.

#### Purpose

- Make the post-search evidence contract explicit and stable.
- Keep candidate evidence assembly in the runner and runtime schemas instead of CLI or report code.

#### Canonical owner

- `src/alphaforge/schemas.py` is the authoritative owner of the candidate-evidence runtime shape.
- `src/alphaforge/experiment_runner.py` is the authoritative owner of assembling validation evidence from search, train, test, and benchmark outputs.
- `src/alphaforge/storage.py` is the authoritative owner of serializing that evidence into persisted validation artifacts.

#### Candidate-evidence fields

- strategy name
- strategy parameters
- optional search ranking context
- train metrics
- test metrics
- benchmark-relative summary
- degradation summary
- artifact paths when produced
- verdict/status

#### Degradation semantics

- return degradation SHALL be calculated as `test_total_return - train_total_return`
- Sharpe degradation SHALL be calculated as `test_sharpe_ratio - train_sharpe_ratio`
- max-drawdown delta SHALL be calculated as `test_max_drawdown - train_max_drawdown`
- the degradation summary SHALL use stable field names and SHALL not invent a larger scoring system

#### Verdict vocabulary

- `candidate`
- `validated`
- `rejected`
- `inconclusive`

#### Verdict semantics

- `candidate` is used for search-only evidence that has not been validated on train/test
- `validated` is used when complete train/test evidence exists and the workflow completed normally
- `rejected` is reserved for explicit rejection policy failures
- `inconclusive` is used when evidence is partial, missing, or insufficient to reach a validated result

#### Scenario: validation evidence includes explicit degradation fields

- GIVEN a candidate has been evaluated on train and test data
- WHEN the validation evidence summary is assembled
- THEN it SHALL include return degradation, Sharpe degradation, and max-drawdown delta using the canonical field names
- AND the verdict SHALL be explicit

### Requirement: walk-forward flows expose fold-level candidate evidence and an aggregate evidence summary

`walk-forward` SHALL expose fold-level candidate evidence for each fold and a separate aggregate evidence summary for the overall walk-forward result.

#### Purpose

- Keep fold-level candidate evidence distinct from the aggregate walk-forward view.
- Avoid collapsing fold-specific selected candidates into a single misleading candidate identity.

#### Canonical owner

- `src/alphaforge/experiment_runner.py` is the authoritative owner of assembling fold evidence and aggregate walk-forward evidence.
- `src/alphaforge.walk_forward_aggregation.py` remains the authoritative owner of aggregate metric calculations.

#### Fold-level evidence

- each fold SHALL carry its own candidate-evidence summary
- fold evidence SHALL include the same candidate-evidence fields as validation evidence whenever the fold produced a searched candidate and a test result

#### Aggregate evidence

- the walk-forward aggregate summary SHALL include:
  - fold count
  - validated fold count
  - skipped fold count
  - aggregate test metrics
  - aggregate benchmark metrics
  - verdict/status
  - artifact paths when produced
- aggregate evidence SHALL be derived from fold evidence and aggregate metrics
- aggregate evidence SHALL be required for returned walk-forward results even when no folds are valid; in that case the verdict SHALL be `inconclusive`

#### Relationship between fold and aggregate summaries

- fold summaries are the source material
- aggregate summaries summarize the fold summaries
- the aggregate summary SHALL not invent a second search rank or a second candidate identity when folds select different candidates

#### Scenario: walk-forward aggregate evidence remains explicit

- GIVEN a walk-forward run returns multiple folds
- WHEN the aggregate evidence summary is assembled
- THEN it SHALL report fold counts and aggregate metrics explicitly
- AND it SHALL not guess a single candidate identity when folds differ
