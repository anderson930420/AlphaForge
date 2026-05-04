# Delta for Report View Model Contract

## ADDED Requirements

### Requirement: reports display minimal evidence diagnostics when present

`src/alphaforge/report.py` SHALL render cost-sensitivity diagnostics and bootstrap evidence diagnostics when those diagnostics are present in the report input metadata or result payload.

#### Scenario: report exposes diagnostic summaries

- GIVEN a research-validation report input contains cost sensitivity and bootstrap evidence
- WHEN the report is rendered
- THEN the HTML SHALL include a cost-sensitivity section
- AND it SHALL include a bootstrap-evidence section
- AND it SHALL present the diagnostics as evidence, not as full execution realism

### Requirement: report wording remains diagnostic-only

The rendered report SHALL describe the diagnostics as minimal research evidence and SHALL NOT claim a full TCA simulator, broker execution simulation, or advanced multiple-testing correction framework.

#### Scenario: report does not overclaim

- GIVEN diagnostic sections are displayed
- WHEN the report is read by a user
- THEN the wording SHALL remain limited to cost sensitivity and bootstrap evidence
- AND it SHALL NOT imply PBO, DSR, White Reality Check, Hansen SPA, or other advanced corrections

