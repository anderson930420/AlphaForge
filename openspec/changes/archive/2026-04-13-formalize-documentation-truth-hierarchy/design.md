# Design: formalize-documentation-truth-hierarchy

## Overview

AlphaForge already has multiple accepted/current OpenSpec contracts that define architecture and module ownership. The remaining risk is not missing runtime behavior, but documentation drift: README, docstrings, CLI help, tests, worklogs, and planning notes can all describe behavior in ways that look authoritative unless the repo explicitly ranks them.

This design makes the OpenSpec contract set the top authority, then classifies every other documentation surface by what it is allowed to do:

- runtime code = executable behavior
- tests = validation evidence
- README and user docs = derived summaries
- docstrings/comments/help text = local explanations
- proposal/design/tasks/worklogs/temp notes = planning or history only

## Why this boundary exists

- The repository now has enough formalized contract specs that documentation ambiguity would create real maintenance debt.
- The same behavior may appear in code, tests, README examples, and planning notes, but only one layer should own the contract.
- Without the hierarchy, contributors may update the wrong artifact first and accidentally create split-brain truth.

## Key design choices

1. Accepted/current OpenSpec specs are the canonical source of truth.
2. Runtime code is subordinate to the canonical spec when a contract exists.
3. Tests are evidence, not authority.
4. README and docstrings can summarize but cannot own architecture.
5. Planning artifacts and worklogs remain non-normative until promoted into accepted/current specs.
6. Conflict resolution must start at the spec layer and then cascade downward.

## Alternatives considered

### Make code the highest authority

Rejected. That would allow accidental behavior to become architecture truth and would undermine the existing contract work already done in OpenSpec.

### Make tests the highest authority

Rejected. Tests are useful evidence, but they are too local and too easy to drift into describing implementation quirks rather than repository-wide ownership.

### Treat README as the primary user-facing truth source

Rejected. README should help users and contributors, but if it is allowed to own cross-module boundaries it becomes a second architecture map.

### Allow planning notes to override current docs until implementation lands

Rejected. That would make in-flight ideas look canonical before they are accepted.

## Migration approach

- Keep accepted/current OpenSpec specs as the canonical target.
- Update README and docs to point at or summarize the canonical specs when they discuss boundaries.
- Treat test updates as evidence of alignment with the canonical contract.
- Leave worklogs, temp notes, and project notes as historical records, not policy sources.

## Residual risk

- Some incidental implementation details still live only in code comments or README examples.
- This is acceptable as long as those surfaces remain clearly subordinate to accepted/current specs and do not introduce new ownership rules.
