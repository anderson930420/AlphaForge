# Proposal: formalize-research-policy-guardrails

## Boundary problem

- AlphaForge now computes more stable validation evidence, fail-fast backtest inputs, and explicit permutation null-model metadata, but promotion/rejection guardrails are not represented as a standalone research policy layer.
- Before GA or broader optimization is added, candidate acceptance rules must be deterministic and separate from metric formulas, execution semantics, null construction, CLI formatting, and reports.
- Without a policy boundary, future search expansion can silently mix optimization, evidence construction, and candidate promotion rules in orchestration code.

## Canonical ownership decision

- `src/alphaforge/research_policy.py` becomes the canonical owner of Research Protocol MVP guardrail decisions.
- `src/alphaforge/metrics.py` remains the owner of metric formulas only.
- `src/alphaforge/backtest.py` remains the owner of execution semantics only.
- `src/alphaforge/permutation.py` remains the owner of permutation/null construction only.
- `src/alphaforge/evidence.py` remains the owner of validation and permutation evidence assembly inputs, not promotion rules.
- `experiment_runner.py` may call the research policy layer later, but it must not define policy rules.
- `storage.py` may persist policy summaries later; persistence is deferred unless required by this small slice.

## Scope

- Add `ResearchPolicyConfig`, `PolicyDecision`, and `evaluate_candidate_policy()` in `src/alphaforge/research_policy.py`.
- Implement candidate promotion rule: a candidate is promoted only when all configured checks pass.
- Implement `max_reruns` as a policy input: `rerun_count <= max_reruns` is allowed; `rerun_count > max_reruns` returns `blocked`.
- Implement permutation procedure scope as explicit policy input, consuming existing metadata when supplied.
- Add focused tests for promotion, rejection, blocking, reasons, and check results.
- Explicitly out of scope:
  - holdout cutoff
  - GA
  - paper parsing / MCP
  - strategy registry
  - live trading
  - new visualization
  - changing metric formulas
  - full-search-procedure permutation
  - automatic runner/CLI integration

## Migration risk

- Existing CLI, validation, permutation, storage, and report behavior remain unchanged because this slice adds a pure policy module and tests.
- No persisted artifact schema changes are required in this slice.
- Future integration must decide when runner workflows call `research_policy.py`; this change only defines the deterministic decision contract.

## Acceptance conditions

- OpenSpec validates for `formalize-research-policy-guardrails`.
- Research policy decisions return one of `promote`, `reject`, or `blocked`.
- Policy decisions include human-readable reasons and per-check boolean results.
- Tests cover all requested guardrails.
- Full pytest passes.
