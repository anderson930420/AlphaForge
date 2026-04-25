# Proposal: tighten-strategy-comparison-type-contracts

## Boundary problem

- `StrategyComparisonResult.research_policy_verdict` currently accepts any string even though research policy decisions have the closed verdict domain `promote`, `reject`, and `blocked`.
- Candidate policy verdicts and research policy verdicts are separate semantic domains, but their type ownership is split between `schemas.py` and `research_policy.py`, causing duplicate type definitions and increasing the risk that comparison results mix the two vocabularies.
- `StrategyFamilySearchConfig.parameter_grid` and runner workflow signatures currently encode search grids as `dict[str, list[int]]`, which makes integer-only grid values appear authoritative even though strategy search parameters should be numeric-only and may include floats in future families.

## Canonical ownership decision

- `src/alphaforge/policy_types.py` becomes the canonical owner for shared policy/search type aliases:
  - `CandidateVerdict`
  - `ResearchPolicyVerdict`
  - `ParameterValue`
  - `ParameterGrid`
- `src/alphaforge/schemas.py` stops defining candidate verdicts locally and imports the shared aliases for schema contracts.
- `src/alphaforge/research_policy.py` stops defining research policy verdicts locally and imports the shared alias.
- Runner, CLI, search, protocol, and test type hints must derive from `ParameterGrid` rather than redefining `dict[str, list[int]]`.

## Scope

- Runtime schema contracts for strategy comparison results, candidate evidence, candidate policy decisions, strategy-family search configs, validation/search/walk-forward runner entrypoints, and CLI request assembly.
- Research policy decision typing.
- Focused tests that assert verdict domains remain distinct and parameter grids accept integer and float numeric values at the schema/type-contract level.
- OpenSpec contract text for multi-strategy comparison type domains and search-grid value scope.

## Migration risk

- CLI behavior risk is low because existing CLI arguments still produce integer lists and the widened alias accepts them.
- Persisted artifact risk is low because JSON serialization already stores numeric values, and the change does not rename fields or change artifact layout.
- Report risk is low because report inputs consume executed `StrategySpec` parameters and comparison summaries, not the alias definitions themselves.
- Test risk is concentrated in imports that previously pulled `CandidateVerdict` from `schemas.py` and in public type hints that currently spell `dict[str, list[int]]`.
- Backward compatibility risk is limited to static type consumers; runtime dataclass construction remains compatible with existing integer grids and verdict strings from the existing policy owners.

## Acceptance conditions

- `CandidateVerdict`, `ResearchPolicyVerdict`, `ParameterValue`, and `ParameterGrid` are defined in `src/alphaforge/policy_types.py`.
- No module defines duplicate candidate or research policy verdict aliases.
- No source workflow signature for search, validate-search, walk-forward, or strategy comparison uses `dict[str, list[int]]` for a parameter grid.
- `StrategyComparisonResult.research_policy_verdict` is typed as `ResearchPolicyVerdict | None`.
- `StrategyFamilySearchConfig.parameter_grid` is typed as `ParameterGrid`.
- Tests prove the research policy verdict domain, candidate verdict domain, and numeric float parameter-grid contract.
- `openspec validate tighten-strategy-comparison-type-contracts --type change --no-interactive` and full `pytest` pass.
