# Design: normalize-validation-return-degradation

## Decision

`return_degradation` keeps its public field name but changes its canonical meaning from raw total-return difference to period-normalized return difference.

The implementation will calculate:

```text
return_degradation = test_metrics.annualized_return - train_metrics.annualized_return
```

## Ownership

- `metrics.py` owns annualized return formula semantics through `MetricReport.annualized_return`.
- `evidence.py` owns degradation-summary assembly and will consume existing `MetricReport` values.
- `policy.py` owns pass/reject decision logic and will continue to consume `return_degradation >= 0`.
- `runner_workflows.py` remains orchestration-only and does not compute this formula.
- `schemas.py` remains unchanged because the existing `degradation_summary` field can express the corrected semantic.

## Implementation plan

1. Update `_build_degradation_summary()` in `src/alphaforge/evidence.py`.
2. Use clear local names for train/test period-normalized returns.
3. Preserve `return_degradation`, `sharpe_degradation`, and `max_drawdown_delta` keys.
4. Add regression tests that prove the field uses annualized returns rather than total returns.
5. Add a policy-facing regression so a candidate is not rejected solely due to lower raw test total return when annualized return degradation is non-negative.

## Compatibility

- No CLI argument changes.
- No runtime dataclass changes.
- No persisted key renames.
- New artifacts will contain the corrected value under the existing `return_degradation` key.

## Out of scope

- holdout cutoff dates
- max reruns
- candidate promotion rule redesign
- permutation null redesign
- target-position index alignment
- GA or broader search-system changes
