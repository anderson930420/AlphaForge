# Proposal: integrate-research-policy-workflow-artifacts

## Boundary problem

- `research_policy.py` already provides a pure, tested policy evaluator for promote/reject/blocked decisions.
- Workflow outputs currently surface older candidate decisions, but they do not consistently persist the research-policy decision shape that the guardrail layer computes.
- Without a persisted policy artifact, the artifact chain stops at evidence and leaves the actual policy verdict implicit in tests or runner internals.

## Canonical ownership decision

- `src/alphaforge/research_policy.py` remains the canonical owner of policy logic and verdict semantics.
- `runner_workflows.py` may evaluate policy decisions after validation evidence is assembled.
- `storage.py` owns persisted policy artifact layout and serializer behavior.
- `cli.py` may surface the persisted policy artifact path through existing JSON payloads, but it must not own policy semantics.
- `metrics.py`, `backtest.py`, `permutation.py`, `evidence.py`, and `research_policy.py` remain unchanged in their respective owners.

## Scope

- Affected workflow: `validate-search`.
- Existing validation evidence already provides train metrics, test metrics, trade count, drawdown, and period-normalized return degradation.
- The workflow will evaluate a research-policy decision from already-computed evidence and persist it alongside validation artifacts.
- The decision is advisory in this slice: it is reported and persisted, but it does not replace the existing validation verdict or halt artifact generation.
- Explicitly out of scope:
  - GA
  - full holdout reveal database
  - paper parsing / MCP
  - strategy registry
  - live trading
  - metric formula changes
  - permutation null redesign
  - walk-forward policy artifact integration, unless it remains trivially small after validate-search wiring

## Migration risk

- Existing validation behavior remains unchanged because the new policy decision is additive.
- The validation summary gains a small policy artifact reference and optional decision payload.
- Existing CLI output tests should continue to pass with minor payload additions.
- Walk-forward policy integration is deferred unless it can reuse the validate-search wiring without broadening scope.

## Acceptance conditions

- OpenSpec validates for `integrate-research-policy-workflow-artifacts`.
- `validate-search` persists a policy decision artifact and surfaces its path in workflow output.
- The serialized policy decision includes candidate ID, verdict, reasons, checks, max reruns, and rerun count.
- Default validation runs produce a policy decision without altering existing validation verdicts.
- Configurable policy thresholds can be passed through the workflow layer without turning the CLI into the policy owner.
