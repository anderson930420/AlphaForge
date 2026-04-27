# artifact-schema-and-output-layout Specification

## MODIFIED Requirements

### Requirement: `storage.py` is the canonical owner of persisted artifact schema and output layout

`src/alphaforge/storage.py` SHALL own the persisted artifact schema, filename, and output layout for the research validation protocol summary artifact.

The research validation protocol workflow SHALL persist a top-level `research_protocol_summary.json` artifact under `output_dir / experiment_name` when persistence is requested.

#### Scenario: research protocol summary uses storage-owned filename and payload

- GIVEN the research validation protocol workflow is run with an output directory and experiment name
- WHEN the workflow persists its protocol summary
- THEN storage MUST write `research_protocol_summary.json` under the workflow root
- AND storage MUST define the JSON payload fields for development evidence, walk-forward evidence, optional permutation evidence, frozen plan, final holdout result, transaction cost assumptions, row counts, periods, and artifact references
- AND CLI and runner code MUST consume storage-owned receipt paths rather than hardcoding a separate persisted schema

#### Scenario: protocol summary artifact does not redefine lower-level artifact schemas

- GIVEN the research protocol summary references development search, walk-forward, permutation, or final holdout artifacts
- WHEN storage serializes the protocol summary
- THEN those nested references MUST remain references or serialized summaries derived from existing runtime/storage contracts
- AND the protocol summary MUST NOT redefine single-run, search, validation, walk-forward, or permutation artifact schemas
