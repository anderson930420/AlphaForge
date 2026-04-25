# Design: tighten-strategy-comparison-type-contracts

## Canonical ownership mapping

- `src/alphaforge/policy_types.py` owns shared policy/search aliases: `CandidateVerdict`, `ResearchPolicyVerdict`, `ParameterValue`, and `ParameterGrid`.
- `src/alphaforge/schemas.py` owns dataclass schema surfaces and imports the aliases rather than redefining them.
- `src/alphaforge/research_policy.py` owns research policy evaluation behavior and imports `ResearchPolicyVerdict` for its decision contract.
- Runner, CLI, protocol, search, storage, and test modules consume `ParameterGrid` when they accept search-grid inputs.

## Contract migration plan

- Add the neutral type module with no imports from `schemas.py` or `research_policy.py` so it cannot participate in the existing schema-to-policy dependency cycle.
- Update schema fields:
  - `StrategyFamilySearchConfig.parameter_grid: ParameterGrid`
  - `StrategyComparisonResult.research_policy_verdict: ResearchPolicyVerdict | None`
  - candidate evidence and policy decision fields continue to use `CandidateVerdict`.
- Update public workflow and facade signatures that accept parameter grids to use `ParameterGrid`.
- Keep runtime serialization unchanged by continuing to serialize grids as mappings of parameter names to value lists.

## Duplicate logic removal plan

- Remove the local `CandidateVerdict` alias from `schemas.py`.
- Remove the local `ResearchPolicyVerdict` alias from `research_policy.py`.
- Update direct imports of `CandidateVerdict` from `alphaforge.schemas` to import from `alphaforge.policy_types`.
- Replace integer-only grid spellings in source workflow signatures with `ParameterGrid`.

## Verification plan

- Add focused tests that inspect type hints for the comparison result verdict fields and strategy-family parameter grid.
- Add tests that construct a strategy-family config with float values without executing an integer-only strategy builder.
- Run repository-wide searches for duplicate verdict aliases and stale integer-only parameter-grid hints.
- Run OpenSpec validation and full pytest.

## Temporary migration states

- No temporary duplicate ownership is planned.
- Existing CLI arguments remain integer-only for current strategy families because widening schema contracts does not require inventing float parameters for MA crossover or breakout execution.
