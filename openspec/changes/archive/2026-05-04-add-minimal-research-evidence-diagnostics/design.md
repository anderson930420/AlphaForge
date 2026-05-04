# Design: Minimal Research Evidence Diagnostics

## Context

AlphaForge already has the core validation engine pieces in place:

- execution semantics are explicit
- trade logging is return-based
- market data validation is strict
- custom-signal validation is file-driven

What remains is minimal research evidence to avoid overstating robustness:

- cost sensitivity under different cost assumptions
- bootstrap confidence intervals for basic return evidence

## Goals

- Keep diagnostics minimal and stable.
- Run diagnostics automatically as part of research validation using documented defaults.
- Surface results in the same summary/report paths already used for research evidence.
- Avoid adding CLI flags unless they become necessary later.

## Non-Goals

- No PBO.
- No Deflated Sharpe Ratio.
- No White Reality Check.
- No Hansen SPA.
- No full TCA simulator.
- No broker execution simulation.
- No limit order book simulation.
- No participation-rate execution engine.
- No ML.
- No portfolio optimization.
- No new strategy features.
- No custom_signal behavior changes.

## Decisions

1. Diagnostics run by default in research-validation flows.
2. Cost sensitivity uses three scenarios: `low_cost`, `base_cost`, and `high_cost`.
3. Cost sensitivity verdicts are based on whether the candidate remains acceptable under the existing research-policy guardrails when evaluated under base and high costs.
4. Bootstrap evidence records sample count, seed, confidence intervals, and a simple verdict based on whether the confidence interval crosses zero.
5. A focused diagnostics module, rather than `backtest.py`, owns the diagnostic formulas.

## Risks and Trade-Offs

- Always-on diagnostics add runtime cost, but they keep the behavior stable and avoid CLI churn.
- The cost-sensitivity verdict is intentionally coarse. That is acceptable for a park-readiness check, but not a substitute for full execution modeling.
- Bootstrap confidence intervals are only a minimal robustness signal. They should not be marketed as a full statistical correction framework.

## Migration Strategy

- Add the summary shapes first.
- Persist them in the research-validation artifacts.
- Render them in reports if present.
- Keep all diagnostics advisory and diagnostic-only.

## Open Questions

- Whether later versions should allow opt-in tuning of bootstrap sample count or cost multipliers is deferred.

