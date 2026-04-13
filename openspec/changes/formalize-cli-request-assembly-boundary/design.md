# Design: formalize-cli-request-assembly-boundary

## Goal

- Make `cli.py` the stable request boundary for AlphaForge without allowing it to become a second owner of domain semantics, storage layout, or report structure.

## Design summary

- Keep parser-level concerns in `cli.py`.
- Keep business validation in the canonical upstream owner for each domain rule.
- Keep workflow coordination in `experiment_runner.py`.
- Keep storage paths and report view-models outside CLI ownership.
- Treat command output as derived presentation data.

## Assembly shape

- `cli.py` should assemble typed request DTOs from argv and dispatch them to the proper orchestration or adapter entrypoints.
- The DTOs themselves remain owned by the modules that define their meaning.
- CLI-specific summaries and JSON payloads should be built only from authoritative return values.

## Migration approach

- Preserve the current command surface.
- Tighten the boundary between parser validation and domain validation.
- Keep composite commands thin and explicit.
- Avoid introducing CLI-local business helpers that duplicate `search.py`, `data_loader.py`, `report.py`, or `storage.py`.

## Risks

- If CLI continues to construct report inputs directly, the report-view-model contract can drift.
- If CLI starts checking semantic conditions like valid window combinations, it will compete with search and execution owners.
- If CLI keeps guessing output paths, terminal payloads will become unreliable.
- If composite commands grow beyond transport logic, CLI can become a second orchestration layer.

