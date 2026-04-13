# Tasks

## 1. Define the CLI request-assembly contract in `src/alphaforge/cli.py`

- Clarify which request DTOs the CLI may assemble and which owners define their meaning.
- Keep CLI local to parsing, typing, dispatch, and presentation formatting.

## 2. Separate syntactic and semantic validation

- Ensure parser-level checks remain in CLI.
- Ensure business-rule validation remains in the authoritative upstream owners.

## 3. Preserve storage, report, and adapter ownership boundaries

- Keep artifact paths and report refs derived from upstream owners only.
- Keep adapter commands transport-level composites only.

## 4. Tighten command-output expectations

- Verify that CLI payloads are derived from authoritative return values and do not invent new canonical schemas.

## 5. Update documentation if required by the new boundary

- Sync any repo docs or spec index entries that still imply CLI is the owner of business semantics or output truth.

