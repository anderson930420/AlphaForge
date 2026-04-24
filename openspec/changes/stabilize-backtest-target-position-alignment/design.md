# Design: stabilize-backtest-target-position-alignment

## Decision

`run_backtest()` will coerce target positions through a small execution-owned helper before assigning them into the runtime frame.

The helper will enforce:

```text
pd.Series input:
  require target_positions.index.equals(market_data.index)
  require len(target_positions) == len(market_data)

list-like / numpy-like input:
  require len(target_positions) == len(market_data)
  assign positionally
```

## Ownership

- `backtest.py` owns this validation because it owns execution semantics and input normalization.
- Strategy implementations remain responsible only for generating strategy-specific target values.
- Runner and CLI layers pass values through and do not duplicate the alignment rule.

## Implementation plan

1. Widen `run_backtest()` input typing to accept `pd.Series` or list-like target positions if needed.
2. Add `_coerce_target_positions(target_positions, data_index)` or equivalent.
3. Use the coerced positional series for the existing float/fill/clip normalization.
4. Preserve all existing fee, slippage, turnover, lag, trade extraction, and equity formulas.
5. Add regression coverage for mismatched Series index, matching Series index, same-length list/numpy input, and length mismatch.

## Compatibility

- Existing strategy-generated signals should continue to pass because they are produced from market-data frames and inherit the same index.
- New failure mode: stale-index `pd.Series` callers receive `ValueError` instead of implicit pandas alignment.
- No schema, artifact, CLI, report, or strategy behavior changes are expected.

## Out of scope

- validation policy
- permutation null model
- holdout cutoff
- max reruns
- candidate promotion rules
- GA
- strategy registry
- changing execution formulas
