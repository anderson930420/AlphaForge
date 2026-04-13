# Tasks: formalize-documentation-truth-hierarchy

## 1. Classify documentation surfaces

- Identify README, module docstrings, inline comments, CLI help text, proposal/design/tasks files, worklogs, daily notes, temp logs, and project notes that describe AlphaForge behavior.
- Mark each surface as canonical, derived, advisory, or historical according to the hierarchy spec.

## 2. Synchronize derived documentation

- Update README and user-facing docs so they summarize accepted/current OpenSpec contracts instead of competing with them.
- Update module docstrings, inline comments, and CLI help text so they explain local behavior without redefining ownership.

## 3. Audit tests and planning artifacts

- Review test names, assertions, and comments for accidental architecture claims.
- Review proposal/design/tasks files and worklogs to ensure they are clearly framed as planning or history rather than current truth.

## 4. Establish maintenance guidance

- Add or update references so future contributors know to check accepted/current OpenSpec specs first.
- Ensure future boundary changes are documented first in OpenSpec and only then reflected in derived docs, tests, and code.
