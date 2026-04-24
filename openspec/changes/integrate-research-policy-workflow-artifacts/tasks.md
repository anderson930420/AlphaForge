# Tasks

## 1. OpenSpec

- [x] 1.1 Create proposal, design, tasks, and delta spec for policy-artifact integration.
- [x] 1.2 Validate the OpenSpec change.

## 2. Implementation

- [x] 2.1 Thread optional research-policy config through validate-search workflow entry points.
- [x] 2.2 Evaluate research-policy decisions after validation evidence is assembled.
- [x] 2.3 Persist research-policy decisions as artifacts and expose their paths in workflow outputs.

## 3. Tests

- [x] 3.1 Add validation coverage for policy decision presence and default promote behavior.
- [x] 3.2 Add coverage for configured rejection, human-readable reasons, and check results.
- [x] 3.3 Add storage coverage for the persisted `policy_decision.json` artifact.
- [x] 3.4 Keep existing validate-search and CLI behavior backward compatible.

## 4. Verification

- [x] 4.1 Run `openspec validate integrate-research-policy-workflow-artifacts --type change --no-interactive`.
- [x] 4.2 Run `pytest`.
- [x] 4.3 Log meaningful implementation and verification steps to Obsidian.
