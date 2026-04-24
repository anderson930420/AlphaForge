# Design: integrate-research-policy-workflow-artifacts

## Decision

`validate-search` will evaluate the already-computed research evidence with `research_policy.evaluate_candidate_policy()` after candidate evidence is assembled.

The workflow will persist a new JSON artifact containing the policy decision shape and a small config snapshot:

```text
candidate_id
verdict
reasons
checks
max_reruns
rerun_count
policy_config
```

The policy decision is advisory in this slice. The existing validation verdict and artifact generation remain intact.

## Ownership

- `research_policy.py` owns policy semantics and verdict computation.
- `runner_workflows.py` owns the orchestration step that calls the evaluator after evidence assembly.
- `storage.py` owns policy artifact filenames, serializer helpers, and receipt paths.
- `experiment_runner.py` forwards the optional policy config through the workflow facade.
- `cli.py` can continue to print the validation payload without learning policy semantics.

## Implementation plan

1. Add policy-config plumbing through the validate-search workflow facade.
2. Evaluate a research policy decision from validation evidence using the existing pure policy layer.
3. Persist a `policy_decision.json` artifact alongside validation outputs.
4. Surface the decision and artifact path in serialized validation output.
5. Add focused tests for default promote behavior, configured rejection, artifact persistence, and backward compatibility.

## Compatibility

- Existing validation behavior stays stable because the policy decision is additive.
- The new artifact path should merge cleanly into existing summary JSON and CLI payloads.
- The change does not add a run-history database, GA, or any new evaluation pipeline.

## Out of scope

- GA
- full one-time holdout reveal database
- paper parsing / MCP
- strategy registry
- live trading
- metric formula changes
- permutation null redesign
- walk-forward policy artifact integration if it would expand beyond a small follow-on change
