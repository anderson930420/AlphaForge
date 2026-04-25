# Tasks

## 1. Spec and contract alignment

- [x] 1.1 Add OpenSpec proposal, design, task list, and spec delta for distinct verdict domains and numeric parameter grids.
- [x] 1.2 Identify source import sites and workflow signatures that currently redefine or narrow the affected contracts.

## 2. Code migration

- [x] 2.1 Add `src/alphaforge/policy_types.py` with shared verdict and parameter-grid aliases.
- [x] 2.2 Update schemas and research policy to import shared aliases and remove duplicate local aliases.
- [x] 2.3 Update CLI, search, runner facade, workflow, protocol, and test type hints to consume `ParameterGrid` where they accept search grids.

## 3. Verification

- [x] 3.1 Add tests proving research policy verdicts, candidate verdicts, and float-capable numeric grids remain distinct contracts.
- [x] 3.2 Run stale-contract searches, OpenSpec validation, and full pytest.

## 4. Cleanup

- [x] 4.1 Mark tasks complete after validation passes.
- [x] 4.2 Log the implementation steps through the local Obsidian workflow.
