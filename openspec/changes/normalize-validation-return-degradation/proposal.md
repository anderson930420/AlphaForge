# Proposal: normalize-validation-return-degradation

## Boundary problem

- Candidate validation evidence currently defines `return_degradation` as `test_total_return - train_total_return`.
- `validate-search` often compares a shorter test segment against a longer train segment, so raw total-return differences encode period length as well as performance quality.
- `src/alphaforge/evidence.py` assembles the degradation summary, while `src/alphaforge/policy.py` consumes `return_degradation >= 0` as part of the validation pass condition. The field meaning must be corrected at the evidence boundary so the policy condition evaluates period-normalized return degradation.

## Canonical ownership decision

- `src/alphaforge/metrics.py` remains the canonical owner of annualized return formulas through `MetricReport.annualized_return`.
- `src/alphaforge/evidence.py` remains the canonical owner of assembling validation degradation evidence and SHALL consume `MetricReport.annualized_return` for return degradation.
- `src/alphaforge/policy.py` remains the canonical owner of policy decisions and SHALL continue consuming the stable `return_degradation` field without redefining how it is calculated.
- `src/alphaforge/runner_workflows.py` remains orchestration-only and SHALL NOT compute or redefine return degradation formulas.
- `src/alphaforge/schemas.py` keeps the existing evidence field names; it does not gain a new schema unless implementation proves the existing contract cannot express the corrected semantic.

## Scope

- Affected contract: candidate validation evidence degradation semantics.
- Affected runtime field: `CandidateEvidenceSummary.degradation_summary["return_degradation"]`.
- Affected code path: validation and walk-forward fold evidence assembly that calls `build_candidate_evidence_summary()`.
- Affected tests: evidence and validation-policy regression tests for period-normalized return degradation.
- Explicitly out of scope:
  - holdout cutoff dates
  - max reruns
  - candidate promotion rule redesign
  - permutation null redesign
  - target-position index alignment
  - GA or optimization framework work
  - public schema field renames

## Migration risk

- CLI behavior remains backward compatible because the field name stays `return_degradation`.
- Persisted validation and walk-forward JSON artifacts keep the same key, but the value changes from raw total-return difference to annualized-return difference.
- Reports that display or consume `return_degradation` inherit the corrected meaning without format changes.
- Tests that asserted the old raw total-return arithmetic must be updated.
- Existing historical artifacts cannot be reinterpreted automatically unless their generation version is known; this change only guarantees semantics for new outputs.

## Acceptance conditions

- OpenSpec validates for `normalize-validation-return-degradation`.
- `return_degradation` is computed as `test_metrics.annualized_return - train_metrics.annualized_return`.
- Validation policy continues to require non-negative `return_degradation`, now referring to period-normalized return degradation.
- Regression coverage proves a shorter test period with lower raw total return but equal or better annualized return is not penalized solely by raw total-return comparison.
- Full pytest passes.
