# Delta for Execution Semantics Contract

## MODIFIED Requirements

### Requirement: Strategy output is a target-position contract, not an order contract

`Strategy.generate_signals()` SHALL produce a canonical target-position series for the next tradable interval, and `backtest.py` SHALL normalize that series into the supported long-flat execution domain.

#### Input alignment contract

- `run_backtest()` SHALL be treated as a public execution boundary.
- target positions SHALL map unambiguously to market-data row order before normalization, lagging, turnover, cost, trade extraction, or equity construction.
- if target positions are supplied as a `pd.Series`, the series index SHALL exactly equal the market-data index.
- if target positions are supplied as list-like or numpy-like values, the input SHALL be accepted positionally only when its length equals the market-data row count.
- any target-position input whose length differs from market data SHALL raise `ValueError`.
- a same-length `pd.Series` with mismatched index labels SHALL raise `ValueError` and SHALL NOT be aligned implicitly by pandas.
- target-position normalization SHALL NOT introduce NaN values through index-label alignment.

#### Scenario: stale target-position series index fails fast

- GIVEN market data with one row order and index
- AND a same-length `pd.Series` of target positions with different index labels
- WHEN `run_backtest()` is called
- THEN it SHALL raise `ValueError`
- AND the error message SHALL mention target-position index alignment
- AND no equity curve or trade log SHALL be produced from implicit pandas alignment

#### Scenario: positional target-position inputs are accepted when length matches

- GIVEN market data with `N` rows
- AND target positions supplied as a list-like or numpy-like object with `N` values
- WHEN `run_backtest()` is called
- THEN the values SHALL be assigned positionally in market-data row order
- AND normal backtest execution SHALL proceed
