# Delta for Storage Artifact Ownership

## ADDED Requirements

### Requirement: research-validation summary artifacts persist minimal evidence diagnostics

`src/alphaforge/storage.py` SHALL persist the cost-sensitivity and bootstrap evidence diagnostics in the canonical research-validation summary artifacts.

The storage-owned artifacts SHALL expose the diagnostics in the persisted `validation_summary.json` and `research_protocol_summary.json` payloads.

#### Scenario: diagnostics survive persistence

- GIVEN research-validation diagnostics have been assembled in memory
- WHEN storage persists the research-validation summary artifacts
- THEN the cost-sensitivity and bootstrap evidence objects SHALL be present in the persisted payloads
- AND the persisted layout SHALL remain storage-owned

### Requirement: storage does not own diagnostic formulas

`storage.py` SHALL serialize diagnostics data but SHALL NOT own the diagnostic formulas, bootstrap resampling, or cost-sensitivity scenario logic.

#### Scenario: storage remains a serializer

- GIVEN the workflow produces diagnostics
- WHEN storage writes the artifacts
- THEN storage SHALL only serialize the supplied diagnostics objects
- AND it SHALL NOT recompute them

