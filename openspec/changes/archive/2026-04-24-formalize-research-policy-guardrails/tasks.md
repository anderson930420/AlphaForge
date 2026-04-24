# Tasks

## 1. OpenSpec

- [x] 1.1 Create proposal, design, tasks, and research-policy spec.
- [x] 1.2 Validate the OpenSpec change.

## 2. Implementation

- [x] 2.1 Inspect existing policy, evidence, permutation summary, and tests.
- [x] 2.2 Add `src/alphaforge/research_policy.py`.
- [x] 2.3 Implement `ResearchPolicyConfig`, `PolicyDecision`, and pure `evaluate_candidate_policy()`.
- [x] 2.4 Keep runner, CLI, storage, metrics, backtest, permutation, and evidence behavior unchanged unless tests require minimal updates.

## 3. Tests

- [x] 3.1 Candidate is promoted when all configured checks pass.
- [x] 3.2 Candidate is rejected when trade count is below threshold.
- [x] 3.3 Candidate is rejected when return degradation is below threshold.
- [x] 3.4 Candidate is rejected when permutation p-value is above configured threshold.
- [x] 3.5 Candidate is rejected or blocked when required null model mismatches.
- [x] 3.6 Candidate is blocked when rerun count exceeds max reruns.
- [x] 3.7 Policy decisions include human-readable reasons.
- [x] 3.8 Policy decisions include check results.

## 4. Verification

- [x] 4.1 Run `openspec validate formalize-research-policy-guardrails --type change --no-interactive`.
- [x] 4.2 Run `pytest`.
- [x] 4.3 Log meaningful implementation and verification steps to Obsidian.
