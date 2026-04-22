# Delta for Search Space and Search Execution Boundary

## ADDED Requirements

### Requirement: `search.py` owns the supported strategy-family set consumed by search-adjacent workflows

`src/alphaforge/search.py` SHALL remain the canonical owner of the supported strategy-family set, and search-adjacent consumers SHALL derive that set from `SUPPORTED_STRATEGY_FAMILIES` instead of maintaining local copies.

#### Purpose

- Keep the named family list authoritative in one place.
- Prevent permutation diagnostics and CLI choices from drifting away from the family set already accepted by search and runner workflows.

#### Canonical owner

- `src/alphaforge/search.py` is the authoritative owner of `SUPPORTED_STRATEGY_FAMILIES`.
- `src/alphaforge/permutation.py` and `src/alphaforge/cli.py` are downstream consumers of that family set when they need to validate or expose supported strategy names.

#### Allowed responsibilities

- `search.py` MAY expose a small explicit tuple of supported family names.
- downstream consumers MAY import and reuse that tuple when their behavior must stay aligned with search-supported families.

#### Explicit non-responsibilities

- `permutation.py` MUST NOT define a second supported-family list for diagnostic strategy construction.
- `cli.py` MUST NOT hardcode a divergent supported-family list for `permutation-test`.

#### Inputs / outputs / contracts

- Input:
  - an explicit strategy-family name
- Output:
  - family-aligned search candidates or family-aligned consumer validation
- Contract rule:
  - any workflow that claims support for a search-supported strategy family must derive the family name set from `search.py`

#### Invariants

- The supported-family set has one authoritative definition.
- Search-adjacent workflows either support a derived subset intentionally or the full canonical set; they do not silently fork the naming contract.
