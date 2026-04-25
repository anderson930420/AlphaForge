# Proposal: formalize-strategy-registry-boundary

## Boundary problem

- Supported strategy-family ownership is currently scattered across `search.py`, `runner_protocols.py`, `permutation.py`, `runner_workflows.py`, and `cli.py`.
- `search.py` defines the supported family tuple and expected parameter names, while runner and permutation code separately dispatch strategy construction through explicit `ma_crossover` / `breakout` branches.
- Train-window validation in `runner_protocols.py` independently maps strategy names to required history parameters, creating a separate source of truth from search parameter metadata.
- CLI choices consume a search-owned constant, but comparison defaults still repeat the current strategy-family names locally.

## Canonical ownership decision

- `src/alphaforge/strategy_registry.py` becomes the canonical owner of supported strategy-family metadata and construction dispatch.
- The registry owns:
  - supported strategy-family names,
  - expected parameter names,
  - integer window-like parameter metadata used by train-window validation,
  - construction from `StrategySpec` to the shared `Strategy` interface.
- `search.py`, `runner_protocols.py`, `runner_workflows.py`, `permutation.py`, and `cli.py` stop owning or redefining supported-family metadata and consume registry helpers instead.
- Concrete strategy modules remain the owners of family-specific signal-generation and parameter validity. The registry dispatches construction; it does not move strategy semantics out of those modules.

## Scope

- New registry module: `src/alphaforge/strategy_registry.py`.
- Existing search-space validation and candidate construction in `src/alphaforge/search.py`.
- Existing runner strategy construction and train-window validation in `src/alphaforge/runner_protocols.py`.
- Existing permutation diagnostic strategy construction in `src/alphaforge/permutation.py`.
- Existing comparison family validation in `src/alphaforge/runner_workflows.py`.
- Existing CLI strategy choices and default comparison strategy list in `src/alphaforge/cli.py`.
- Focused registry tests plus existing search, runner, CLI, permutation, and strategy tests.

## Migration risk

- CLI behavior risk is limited to preserving the existing supported choices `ma_crossover` and `breakout`; the registry must expose the same names in the same deterministic order.
- Persisted artifact risk is low because this change does not alter output paths, JSON fields, CSV columns, artifact schemas, ranking, or policy outputs.
- Runtime compatibility risk is concentrated in construction dispatch and error messages for unsupported strategy names.
- Test risk is concentrated in tests that currently import `SUPPORTED_STRATEGY_FAMILIES` from `search.py` or assert direct runner construction behavior.
- Future extensibility risk is reduced only at the boundary level: adding a new family should primarily require a registry registration plus strategy-specific tests, not new ad hoc branches across search, runner, protocol, or permutation modules.

## Acceptance conditions

- The proposal, design, tasks, and spec delta exist and validate before runtime implementation begins.
- `strategy_registry.py` defines explicit registrations for exactly `ma_crossover` and `breakout`.
- Registry helpers expose supported families, registration lookup, and strategy construction.
- Search expected-parameter validation derives from registry metadata.
- Runner/protocol strategy construction derives from the registry.
- Train-window validation derives integer window-like parameters from the registry.
- CLI choices and comparison defaults derive from the registry-backed supported-family list.
- Unsupported strategy errors include the unsupported name and supported strategy names.
- No independent `SUPPORTED_STRATEGY_FAMILIES` source of truth remains outside the registry.
- OpenSpec validation and the full pytest suite pass.
