# Delta for Research Policy Guardrails

## ADDED Requirements

### Requirement: Research policy guardrails are evaluated by a dedicated pure policy module

AlphaForge SHALL expose a dedicated research policy layer that decides whether already-computed candidate evidence is promoted, rejected, or blocked.

#### Purpose

- Keep promotion/rejection guardrails separate from metric formulas, execution semantics, permutation null construction, evidence assembly, CLI formatting, and reports.
- Establish deterministic guardrails before GA or broader optimization workflows are added.

#### Canonical owner

- `src/alphaforge/research_policy.py` is authoritative for Research Protocol MVP policy guardrail decisions.

#### Policy inputs

- candidate id, if available
- candidate evidence summary
- optional permutation summary
- research policy configuration
- rerun count

#### Policy outputs

- candidate id
- verdict: `promote`, `reject`, or `blocked`
- human-readable reasons
- per-check boolean results
- max reruns
- rerun count

#### Policy configuration

- `max_reruns`
- `min_trade_count`
- `max_drawdown_cap`
- `min_return_degradation`
- `max_permutation_p_value`
- `required_permutation_null_model`
- `required_permutation_scope`

#### Ownership exclusions

- `metrics.py` owns metric formulas only.
- `backtest.py` owns execution semantics only.
- `permutation.py` owns permutation/null construction only.
- `evidence.py` owns validation and permutation evidence assembly only.
- runner, CLI, storage, and report layers SHALL NOT define promotion rules.

#### Scenario: candidate is promoted only when configured checks pass

- GIVEN candidate evidence and optional permutation evidence satisfy all configured policy checks
- WHEN the research policy evaluator runs
- THEN the decision verdict SHALL be `promote`
- AND the decision SHALL include check results
- AND the decision SHALL include human-readable reasons

#### Scenario: candidate is rejected when a configured evidence check fails

- GIVEN candidate evidence fails a configured trade count, drawdown, return degradation, permutation p-value, null model, or permutation scope check
- WHEN the research policy evaluator runs
- THEN the decision verdict SHALL be `reject`
- AND the failed check SHALL be represented in the decision checks
- AND the reason list SHALL identify the failed guardrail

#### Scenario: candidate is blocked when max reruns is exceeded

- GIVEN `rerun_count` is greater than `max_reruns`
- WHEN the research policy evaluator runs
- THEN the decision verdict SHALL be `blocked`
- AND the decision SHALL preserve both `max_reruns` and `rerun_count`

### Requirement: Research policy defines promotion rule, max reruns, and permutation procedure scope without implementing future workflows

Research policy SHALL define the current candidate promotion rule, max-rerun guardrail, and permutation procedure-scope guardrail without implementing holdout access control, GA, or full-search-procedure permutation.

#### Candidate promotion rule

- A candidate is promoted only if every configured policy check passes.
- Any failed configured evidence or permutation check rejects the candidate unless the rerun guardrail blocks the candidate first.

#### Max reruns

- `rerun_count <= max_reruns` is allowed.
- `rerun_count > max_reruns` returns `blocked`.
- No run-history database is required for this change.

#### Permutation procedure scope

- The current default permutation procedure scope is `candidate_fixed`.
- If permutation evidence contains explicit scope metadata, policy SHALL consume it.
- Full-search-procedure permutation is not implemented by this requirement.

#### Explicitly out of scope

- holdout cutoff
- GA
- paper parsing / MCP
- strategy registry
- live trading
- new visualization
- changing metric formulas
- full-search-procedure permutation

#### Scenario: permutation scope is checked when configured

- GIVEN a required permutation scope is configured
- AND permutation evidence supplies a matching scope or omits scope while using the current `candidate_fixed` default
- WHEN the research policy evaluator runs
- THEN the permutation scope check SHALL pass

#### Scenario: holdout and GA remain out of scope

- GIVEN the research policy layer is evaluated
- WHEN it returns a decision
- THEN it SHALL NOT enforce holdout cutoff access
- AND it SHALL NOT run GA
- AND it SHALL NOT generate or re-rank candidates
