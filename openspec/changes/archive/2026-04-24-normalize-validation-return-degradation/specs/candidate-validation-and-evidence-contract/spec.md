# Delta for Candidate Validation and Evidence Contract

## MODIFIED Requirements

### Requirement: validation flows expose a canonical candidate-evidence summary

`validate-search` SHALL produce a canonical candidate-evidence summary for the searched candidate it evaluates on the train/test split.

#### Degradation semantics

- return degradation SHALL be calculated as `test_annualized_return - train_annualized_return`
- `return_degradation` SHALL mean period-normalized return degradation, not raw total-return degradation
- annualized return values SHALL come from `MetricReport.annualized_return`, whose formula is owned by `src/alphaforge/metrics.py`
- Sharpe degradation SHALL be calculated as `test_sharpe_ratio - train_sharpe_ratio`
- max-drawdown delta SHALL be calculated as `test_max_drawdown - train_max_drawdown`
- the degradation summary SHALL use stable field names and SHALL not invent a larger scoring system

#### Scenario: validation return degradation is period-normalized

- GIVEN a candidate has been evaluated on train and test data with unequal segment lengths
- AND the test segment has lower raw total return than the train segment
- AND the test annualized return is equal to or greater than the train annualized return
- WHEN the validation evidence summary is assembled
- THEN `return_degradation` SHALL be non-negative
- AND the validation policy SHALL NOT fail solely because test raw total return is lower than train raw total return
