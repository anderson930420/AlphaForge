# Delta for CLI Request Assembly Boundary

## ADDED Requirements

### Requirement: `permutation-test` uses the same explicit strategy-family selection style as the rest of the CLI

`src/alphaforge/cli.py` SHALL parse an explicit `--strategy` selector for `permutation-test` and assemble the fixed `StrategySpec` through the same family-selection style already used by the core workflow commands.

#### Purpose

- Keep CLI request assembly consistent across command surfaces.
- Prevent the permutation command from remaining a special MA-only parser path after the repo gained a second supported family.

#### Canonical owner

- `src/alphaforge/cli.py` remains the authoritative owner of `permutation-test` argument parsing and request assembly.
- `src/alphaforge/permutation.py` remains the authoritative owner of diagnostic execution semantics.

#### Allowed responsibilities

- `cli.py` MAY expose `--strategy` on `permutation-test` with choices derived from `SUPPORTED_STRATEGY_FAMILIES`.
- `cli.py` MAY assemble MA crossover fixed-candidate parameters from `--short-window` and `--long-window`.
- `cli.py` MAY assemble breakout fixed-candidate parameters from `--lookback-window`.

#### Explicit non-responsibilities

- `cli.py` MUST NOT hardcode a MA-only diagnostic request when the caller selected a different supported strategy family.
- `cli.py` MUST NOT become the owner of diagnostic strategy construction semantics.
- `cli.py` MUST NOT infer strategy family from which optional flags happened to be present when `--strategy` already names it.

#### Inputs / outputs / contracts

- Inputs:
  - `--strategy`
  - family-specific fixed-candidate parameters
  - permutation configuration flags
- Output:
  - one fixed `StrategySpec` passed through to the diagnostic owner
- Contract rules:
  - MA crossover requires `--short-window` and `--long-window`
  - breakout requires `--lookback-window`
  - the assembled `StrategySpec.name` matches the CLI-selected family

#### Invariants

- `permutation-test` remains syntactic at the CLI layer.
- Family-specific parameter requirements are surfaced as parser errors, not hidden runtime fallbacks.
