# Delta for Holdout Data Boundary Contract

## ADDED Requirements

### Requirement: Canonical market data can be split into development and holdout regions by cutoff

`split_holdout_data()` or an equivalent data-loading helper SHALL partition canonical market data around `holdout_cutoff_date`, where the cutoff marks the first datetime in the final holdout region.

The helper SHALL:

- require a `datetime` column
- parse the cutoff date consistently
- return development rows with `datetime < holdout_cutoff_date`
- return holdout rows with `datetime >= holdout_cutoff_date`
- preserve canonical columns and row order
- raise `ValueError` when the cutoff cannot be parsed
- raise `ValueError` when the `datetime` column is missing
- raise `ValueError` when the development partition would be empty
- raise `ValueError` when the holdout partition would be empty

#### Scenario: the split returns development and holdout partitions

- GIVEN canonical market data with an ascending `datetime` column
- AND a cutoff date that falls inside the available range
- WHEN the holdout split helper is called
- THEN the development partition SHALL contain only rows before the cutoff
- AND the holdout partition SHALL contain only rows on or after the cutoff
- AND both partitions SHALL preserve the canonical OHLCV column order
- AND both partitions SHALL preserve the original row order

#### Scenario: a cutoff that removes all development rows fails fast

- GIVEN canonical market data
- AND a cutoff date that is less than or equal to the first available datetime
- WHEN the holdout split helper is called
- THEN it SHALL raise `ValueError`

#### Scenario: a cutoff that removes all holdout rows fails fast

- GIVEN canonical market data
- AND a cutoff date that is later than the last available datetime
- WHEN the holdout split helper is called
- THEN it SHALL raise `ValueError`

#### Scenario: invalid cutoff parsing fails fast

- GIVEN canonical market data
- AND an unparseable cutoff value
- WHEN the holdout split helper is called
- THEN it SHALL raise `ValueError`

### Requirement: Normal research workflows use development-only data when a holdout cutoff is configured

Search, validate-search, walk-forward, and permutation-test workflows SHALL operate only on development rows when `holdout_cutoff_date` is configured.

Workflow output metadata that already supports dictionaries SHOULD record:

- `holdout_cutoff_date`
- `development_rows`
- `holdout_rows`

#### Scenario: validate-search excludes holdout rows from train/test workflows

- GIVEN canonical market data and a configured `holdout_cutoff_date`
- WHEN `validate-search` is executed
- THEN the validation workflow SHALL consume only rows with `datetime < holdout_cutoff_date`
- AND the resulting metadata SHALL record the cutoff and partition sizes

#### Scenario: workflows without a cutoff remain unchanged

- GIVEN canonical market data
- AND no `holdout_cutoff_date`
- WHEN a normal research workflow is executed
- THEN it SHALL continue to operate on the full loaded dataset
