# Design: formalize-research-policy-guardrails

## Decision

Add a new pure module:

```text
src/alphaforge/research_policy.py
```

This module evaluates already-computed evidence. It does not run workflows, compute metrics, build permutation nulls, or persist artifacts.

## Data contracts

`ResearchPolicyConfig`:

- `max_reruns: int = 0`
- `min_trade_count: int = 1`
- `max_drawdown_cap: float | None = None`
- `min_return_degradation: float = 0.0`
- `max_permutation_p_value: float | None = None`
- `required_permutation_null_model: str | None = "return_block_reconstruction"`
- `required_permutation_scope: str | None = None`

`PolicyDecision`:

- `candidate_id: str | None`
- `verdict: Literal["promote", "reject", "blocked"]`
- `reasons: list[str]`
- `checks: dict[str, bool]`
- `max_reruns: int`
- `rerun_count: int`

## Evaluation rules

- Block when `rerun_count > max_reruns`.
- Reject when `trade_count < min_trade_count`.
- Reject when `max_drawdown` breaches configured cap.
- Reject when `return_degradation < min_return_degradation`.
- Reject when permutation p-value exceeds configured maximum.
- Reject when required null model does not match.
- Reject when required permutation scope does not match.
- Promote only when all configured checks pass.

## Permutation procedure scope

- If a permutation summary includes `metadata["permutation_scope"]`, consume it.
- If no scope is present, use the current fixed-candidate default `"candidate_fixed"`.
- This change does not implement full-search-procedure permutation.

## Persistence

- No policy artifact persistence in this slice.
- Persistence is deferred because the requested guardrail behavior can be tested as a pure function without changing storage contracts.

## Out of scope

- holdout cutoff
- GA
- paper parsing / MCP
- strategy registry
- live trading
- new visualization
- changing metric formulas
- automatic runner/CLI integration
