# Delta for Research Validation Protocol

## ADDED Requirements

### Requirement: research validation always emits minimal evidence diagnostics

The runtime research validation workflow SHALL emit cost-sensitivity diagnostics and bootstrap evidence diagnostics for the selected candidate using documented default diagnostic parameters.

The workflow SHALL remain research-validation oriented and SHALL NOT add PBO, DSR, White Reality Check, Hansen SPA, full TCA, broker execution simulation, or limit-order-book simulation.

#### Scenario: diagnostics are emitted by default

- GIVEN a valid research-validation request
- WHEN the workflow evaluates the selected candidate
- THEN it SHALL compute cost sensitivity diagnostics
- AND it SHALL compute bootstrap evidence diagnostics
- AND it SHALL include those diagnostics in the research-validation outputs by default

#### Scenario: advanced diagnostics remain out of scope

- GIVEN the workflow runs with minimal diagnostics enabled
- WHEN the outputs are assembled
- THEN the workflow SHALL NOT claim to implement PBO, DSR, White Reality Check, Hansen SPA, or a full execution simulator

### Requirement: research protocol summary exposes diagnostics alongside evidence and holdout results

`research_protocol_summary.json` SHALL include the minimal evidence diagnostics for the selected candidate alongside the existing development evidence and final holdout result.

The summary SHALL expose:

- the selected candidate evidence
- the cost-sensitivity diagnostic
- the bootstrap evidence diagnostic
- the final holdout result

#### Scenario: protocol summary includes evidence diagnostics

- GIVEN the research-validation workflow completes
- WHEN the protocol summary is persisted or returned
- THEN the summary SHALL contain cost sensitivity and bootstrap evidence
- AND the diagnostics SHALL be clearly associated with the selected candidate

### Requirement: research validation delegates diagnostics to a focused diagnostics module

`runner_workflows.py` SHALL orchestrate diagnostics generation but SHALL NOT own diagnostic formulas.

The diagnostic formulas and resampling / scenario logic SHALL be owned by a focused module such as `src/alphaforge/evidence_diagnostics.py`.

#### Scenario: workflow orchestration remains thin

- GIVEN a research-validation run needs diagnostics
- WHEN the workflow executes
- THEN it SHALL delegate diagnostics to the focused diagnostics owner
- AND it SHALL NOT reimplement cost-sensitivity or bootstrap formulas inside orchestration code

