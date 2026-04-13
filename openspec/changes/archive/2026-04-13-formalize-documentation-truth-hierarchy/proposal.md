# Proposal: formalize-documentation-truth-hierarchy

## Boundary problem

- AlphaForge now has several accepted/current contract specs that define ownership and behavior for execution, market data, persistence, reporting, CLI request assembly, search, and runner orchestration.
- The repository still contains many other documentation surfaces that describe system behavior: README files, module docstrings, inline comments, CLI help text, proposal/design/tasks files, tests, worklogs, daily notes, temp logs, and project notes.
- Without an explicit truth hierarchy, those surfaces can drift into competing with canonical contracts and make it unclear what to trust when documents disagree.

## Canonical authority decision

- Accepted/current OpenSpec specs are the canonical contract truth for AlphaForge.
- Runtime code is executable behavior that should align with accepted/current specs, but code behavior alone does not redefine architecture ownership once a contract exists.
- Tests are validation evidence, not architecture owners.
- README and user-facing docs are derived summaries and usage guides, not canonical contract sources.
- Module docstrings, inline comments, and CLI help text are local explanatory artifacts only.
- Proposal/design/tasks files, worklogs, daily notes, temp logs, and project notes are planning or historical working-memory artifacts only.

## Scope

- Define the documentation truth hierarchy across canonical specs, code, tests, README, docstrings, CLI help text, and planning/history artifacts.
- Freeze the conflict-resolution order when sources disagree.
- Clarify when lower-authority documentation must be updated after a canonical contract changes.
- Provide concrete examples so future maintainers can tell authoritative truth from explanatory or historical text.

## Migration risk

- README can accidentally become a second architecture map if it is treated as authoritative.
- Docstrings and CLI help can accidentally define cross-module ownership if they are read as canonical instead of explanatory.
- Tests can be mistaken for architecture truth even though they only validate behavior.
- Proposal/design/tasks files and worklogs can be mistaken for current truth even though they are planning or historical records.
- When multiple sources disagree, contributors can waste time editing the wrong layer first unless the hierarchy is explicit.

## Acceptance conditions

- The repo has one explicit, documented authority order for architecture and contract truth.
- Accepted/current OpenSpec specs outrank README, docstrings, tests, CLI help text, and planning/history artifacts.
- Lower-authority documentation is clearly labeled as derived, advisory, or historical.
- Conflict resolution and update responsibilities are stated clearly enough that future maintainers can apply the hierarchy without guessing.
