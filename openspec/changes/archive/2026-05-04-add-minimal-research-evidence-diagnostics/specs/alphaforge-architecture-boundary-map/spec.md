# Delta for AlphaForge Architecture Boundary Map

## ADDED Requirements

### Requirement: focused research evidence diagnostics have a single owner

AlphaForge SHALL assign cost-sensitivity and bootstrap-evidence formulas to a focused diagnostics module rather than to `backtest.py`, `storage.py`, or `report.py`.

#### Scenario: diagnostics remain outside the execution owner

- GIVEN research evidence diagnostics are computed
- WHEN ownership is assigned
- THEN `src/alphaforge/evidence_diagnostics.py` SHALL be the canonical owner of the diagnostic formulas
- AND `backtest.py` SHALL remain execution semantics only
- AND `storage.py` and `report.py` SHALL remain serializer / presentation consumers only

### Requirement: research-validation orchestration remains orchestration only

`runner_workflows.py` SHALL orchestrate minimal evidence diagnostics as part of research validation but SHALL NOT own the diagnostic formulas or evidence semantics.

#### Scenario: workflow remains a coordinator

- GIVEN a research-validation workflow produces diagnostics
- WHEN the architecture map is consulted
- THEN `runner_workflows.py` SHALL be described as orchestration only
- AND the diagnostics module SHALL own the formulas

