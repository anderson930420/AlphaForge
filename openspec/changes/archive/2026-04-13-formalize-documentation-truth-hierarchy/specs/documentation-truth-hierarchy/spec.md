# Delta for Documentation Truth Hierarchy

## Authority hierarchy

AlphaForge SHALL treat documentation and runtime surfaces according to the following authority order, from highest to lowest:

1. Accepted/current OpenSpec specs under `openspec/specs/`
2. Runtime code behavior, only for incidental implementation details not already governed by an accepted/current spec
3. Tests, as validation evidence only
4. README files and other user-facing docs, as derived summaries and usage guides only
5. Module docstrings, inline comments, and CLI help text, as local explanatory artifacts only
6. Proposal, design, and tasks files inside in-flight OpenSpec changes, as planning artifacts only
7. Worklogs, daily notes, temp logs, project briefs, scratch notes, and other historical or local working-memory artifacts, as non-normative records only

## Normative vs derived vs advisory vs historical

- Normative / canonical:
  - accepted/current OpenSpec specs
- Derived / explanatory:
  - README files
  - module docstrings
  - inline comments
  - CLI help text
- Advisory / local guidance:
  - tests
  - project briefs
- Historical / planning only:
  - proposal.md
  - design.md
  - tasks.md
  - worklogs
  - daily notes
  - temp logs
  - scratch notes

## ADDED Requirements

### Requirement: accepted/current OpenSpec specs are the canonical source of AlphaForge contract and ownership truth

Accepted/current OpenSpec specs SHALL be the single canonical source of architecture, ownership, and contract truth for AlphaForge.

#### Purpose

- Prevent README, tests, docstrings, help text, or planning notes from becoming parallel contract owners.
- Give maintainers one explicit place to resolve module ownership, cross-module semantics, and boundary definitions.

#### Canonical owner

- `openspec/specs/*` accepted/current specs are the authoritative source for:
  - module ownership,
  - cross-module contract semantics,
  - canonical input and output boundaries,
  - canonical terminology for AlphaForge runtime behavior.
- `openspec/changes/*` proposal, design, and tasks files are not authoritative once a spec has been accepted/current.
- Archived change artifacts are historical records only and do not supersede current specs.

#### Allowed responsibilities

- Accepted/current OpenSpec specs MAY:
  - define module ownership boundaries,
  - assign canonical meaning to runtime contracts,
  - define what downstream modules may rely on,
  - document conflict-resolution order for other layers,
  - be referenced by docs, comments, and tests as the normative source.

#### Explicit non-responsibilities

- Accepted/current OpenSpec specs MUST NOT be treated as implementation code.
- In-flight proposal, design, and tasks files MUST NOT be treated as current truth.
- Archived change artifacts MUST NOT be treated as current truth.
- This hierarchy spec MUST NOT reassign ownership already established by accepted/current domain specs; it only clarifies how documentation layers relate to them.

#### Inputs / outputs / contracts

- Inputs:
  - accepted/current OpenSpec specs
  - in-flight OpenSpec change artifacts
  - archived OpenSpec change artifacts
  - runtime code
  - tests
  - README and user-facing docs
  - module docstrings, comments, and CLI help
  - worklogs, daily notes, temp logs, and project notes
- Outputs:
  - canonical contract truth
  - derived explanations
  - advisory validation evidence
  - historical planning records

#### Invariants

- There is exactly one canonical source of contract truth: accepted/current OpenSpec specs.
- Lower-authority documentation may summarize or explain canonical truth, but it may not create a competing owner.
- A planning artifact becomes authoritative only if it is promoted into an accepted/current spec.

#### Cross-module dependencies

- All runtime modules must treat accepted/current specs as the top-level contract reference.
- All docs and comments that describe cross-module ownership must defer to accepted/current specs.
- Tests must validate against accepted/current specs rather than defining their own architecture.

#### Failure modes if this boundary is violated

- README starts acting like a second architecture map.
- Proposal notes or worklogs are mistaken for current contract truth.
- Contributors edit the wrong layer first because no source of truth is obvious.
- Multiple modules start using different mental models for the same boundary.

#### Migration notes from current implementation

- AlphaForge already has several accepted/current contract specs for execution, market data, persistence, reporting, CLI, search, and runner boundaries.
- The repository also has README and project notes that describe those same behaviors, so the hierarchy must explicitly demote them to derived or advisory status.

#### Open questions / deferred decisions

- Whether archived accepted changes should be referenced in docs as historical rationale is deferred.
  - Recommended default: allow historical citation, but never treat archived change artifacts as current authority.
- Whether `openspec/specs/` should be mirrored by a generated index is deferred.
  - Recommended default: keep the current spec tree canonical and add indexes only as derived navigation aids.

#### Scenario: accepted/current specs outrank every other documentation layer

- GIVEN a README sentence conflicts with an accepted/current OpenSpec spec
- WHEN a maintainer needs to determine contract truth
- THEN the accepted/current OpenSpec spec SHALL prevail
- AND the README SHALL be updated to match or explicitly marked as outdated

### Requirement: runtime code is executable behavior, not architecture authority

Runtime code SHALL be treated as executable behavior that should align with accepted/current specs, not as the final source of architecture ownership once a contract exists.

#### Purpose

- Prevent observed implementation details from silently redefining ownership or higher-level contracts.
- Allow the repo to detect and repair implementation drift without letting drift become the standard.

#### Canonical owner

- Runtime modules are authoritative only for their implemented behavior within the boundaries already assigned by accepted/current specs.
- Runtime code is not authoritative for cross-module ownership if an accepted/current spec already assigns that ownership elsewhere.

#### Allowed responsibilities

- Runtime code MAY:
  - implement the behavior described by accepted/current specs,
  - expose incidental implementation details not yet formalized in a spec,
  - serve as empirical evidence of current behavior when a spec is silent.

#### Explicit non-responsibilities

- Runtime code MUST NOT redefine architecture ownership that an accepted/current spec already assigns.
- Runtime code MUST NOT be used to override a published contract merely because it is currently deployed.
- Runtime code MUST NOT be treated as the canonical source for documentation hierarchy rules.

#### Inputs / outputs / contracts

- Inputs:
  - accepted/current specs
  - runtime implementation state
  - test expectations
  - documentation surfaces
- Outputs:
  - executable behavior
  - observed behavior for debugging
  - implementation drift when code diverges from the canonical contract

#### Invariants

- When runtime code and accepted/current specs disagree on a covered contract, the code is drift, not authority.
- When a detail is not covered by any accepted/current spec, runtime code may be consulted as the current implementation reference until the detail is formalized.
- The presence of code does not by itself create a new contract owner.

#### Cross-module dependencies

- Every runtime module is downstream of the applicable accepted/current specs.
- Documentation layers may describe code behavior, but they must not elevate code-local details into cross-module truth without an explicit spec.

#### Failure modes if this boundary is violated

- Temporary implementation quirks are mistaken for architecture decisions.
- Contributors preserve accidental behavior because it appears in code, even though the canonical contract says otherwise.
- New specs are rejected in favor of current behavior instead of using current behavior as a refactoring target.

#### Migration notes from current implementation

- AlphaForge has already accumulated code paths that implement boundaries later formalized in OpenSpec.
- This means some code may predate a current spec, so the hierarchy must make clear that the accepted/current spec is the contract reference and the code is the thing to align.

#### Open questions / deferred decisions

- Whether code-local comments can ever be used to document unresolved implementation details that are not yet in spec is deferred.
  - Recommended default: yes, but only as local explanation and never as cross-module ownership.

#### Scenario: current code does not override an accepted/current spec

- GIVEN runtime code implements a behavior that conflicts with an accepted/current spec
- WHEN a maintainer resolves the discrepancy
- THEN the code SHALL be treated as drift
- AND the canonical contract SHALL remain the accepted/current spec until a new spec change intentionally replaces it

### Requirement: tests are validation evidence, not architecture owners

Tests SHALL validate behavior against canonical contracts, but they SHALL NOT define architecture ownership or business semantics on their own.

#### Purpose

- Prevent test names, fixtures, and assertions from becoming hidden truth owners.
- Keep tests useful as evidence while preserving the canonical role of OpenSpec specs.

#### Canonical owner

- Tests are authoritative only for whether the current implementation passes or fails the asserted behavior.
- Tests are not authoritative for module ownership, contract hierarchy, or business semantics if those are already defined by accepted/current specs.

#### Allowed responsibilities

- Tests MAY:
  - describe expected behavior in executable form,
  - detect drift from accepted/current specs,
  - serve as regression evidence for canonical contracts,
  - provide examples of intended use.

#### Explicit non-responsibilities

- Tests MUST NOT define architecture ownership.
- Tests MUST NOT become the source of a new cross-module contract unless a corresponding accepted/current spec exists or is being created.
- Test names, comments, and fixtures MUST NOT be treated as canonical truth when they conflict with accepted/current specs.

#### Inputs / outputs / contracts

- Inputs:
  - accepted/current specs
  - runtime code
  - fixtures and expected outputs
- Outputs:
  - pass/fail evidence
  - regression coverage
  - examples of intended behavior

#### Invariants

- Tests are subordinate to accepted/current specs.
- When tests and accepted/current specs disagree, the spec is the contract and the tests need review.
- Test comments are explanatory only unless the corresponding spec says otherwise.

#### Cross-module dependencies

- Runtime code should be tested against accepted/current specs.
- README and docs may cite tests as examples, but not as contract owners.
- CI and local verification use tests as evidence that the implementation matches the current contract.

#### Failure modes if this boundary is violated

- A test comment becomes a de facto architecture rule.
- Different test files encode different versions of the same contract.
- Maintainers keep behavior because tests currently assert it even though the canonical spec has changed.

#### Migration notes from current implementation

- AlphaForge already has focused pytest coverage for core modules and CLI flows.
- Those tests are valuable evidence, but they still need to be read through the lens of the accepted/current specs rather than as independent sources of ownership truth.

#### Open questions / deferred decisions

- Whether some contract-specific tests should be promoted into executable examples in docs is deferred.
  - Recommended default: keep tests in the validation layer and mirror only user-facing examples into README or docs when useful.

#### Scenario: a failing test does not change ownership

- GIVEN a test file comments that a module “owns” a boundary differently from the accepted/current spec
- WHEN the discrepancy is reviewed
- THEN the accepted/current spec SHALL prevail
- AND the test SHOULD be updated to reflect the canonical contract, not the reverse

### Requirement: README, user-facing docs, docstrings, comments, and CLI help text are derived or local explanatory artifacts only

README files, user-facing docs, module docstrings, inline comments, and CLI help text SHALL explain or summarize canonical truth, but they SHALL NOT define new contract truth.

#### Purpose

- Keep documentation helpful without allowing it to compete with canonical specs.
- Make it obvious which text is explanatory and which text is normative.

#### Canonical owner

- README and user-facing docs are authoritative only for how AlphaForge is explained to users, not for architecture truth.
- Module docstrings, inline comments, and CLI help text are authoritative only for local readability and command guidance.

#### Allowed responsibilities

- Derived and local explanatory artifacts MAY:
  - summarize accepted/current specs in plain language,
  - provide usage examples,
  - explain local implementation details that do not redefine cross-module ownership,
  - point readers back to the canonical spec when a boundary matters.

#### Explicit non-responsibilities

- README MUST NOT be the source of truth for architecture ownership.
- Module docstrings and comments MUST NOT create new cross-module contract rules.
- CLI help text MUST NOT introduce a different canonical schema or boundary than the accepted/current specs and runtime contracts.
- Explanatory artifacts MUST NOT resolve conflicts by themselves when they disagree with accepted/current specs.

#### Inputs / outputs / contracts

- Inputs:
  - accepted/current specs
  - runtime behavior
  - command surface and module-local behavior
- Outputs:
  - usage notes
  - short summaries
  - local explanations
  - links or references to canonical specs

#### Invariants

- Explanatory artifacts may be updated to reflect canonical specs, but they do not own those specs.
- A README can summarize the canonical output layout, but the output layout itself is owned elsewhere.
- Docstrings can explain a helper’s behavior, but they cannot assign that helper new ownership.

#### Cross-module dependencies

- README should point to canonical OpenSpec specs when describing cross-module boundaries.
- CLI help text should remain aligned with request-assembly contracts and not reinterpret them.
- Module comments should be read as implementation notes, not architecture policy.

#### Failure modes if this boundary is violated

- README becomes a competing architecture map.
- CLI help text advertises behavior that the runtime or canonical specs do not support.
- Docstrings or comments start contradicting the actual contract and confuse future maintainers.

#### Migration notes from current implementation

- AlphaForge README and module docstrings already describe current capabilities and output structure.
- That is useful, but the text must now be treated as derived and synchronized to accepted/current specs rather than treated as a parallel authority.

#### Open questions / deferred decisions

- Whether every user-facing doc should include an explicit “canonical source” link is deferred.
  - Recommended default: add links where cross-module behavior is described, especially for boundaries that frequently drift.

#### Scenario: README may summarize, but not own, the canonical contract

- GIVEN the README describes the search output layout
- WHEN the canonical storage spec changes that layout
- THEN the README SHALL be updated to summarize the new canonical layout
- AND the README SHALL NOT be treated as the owner of that layout

### Requirement: proposal, design, tasks, worklogs, daily notes, temp logs, project briefs, and scratch notes are historical or planning artifacts only

Planning and working-memory artifacts SHALL remain non-normative unless they are promoted into accepted/current OpenSpec specs.

#### Purpose

- Prevent in-flight design notes and local logs from being mistaken for current architecture truth.
- Preserve the value of planning artifacts without letting them compete with the canonical contract set.

#### Canonical owner

- `proposal.md`, `design.md`, and `tasks.md` inside `openspec/changes/*` are authoritative only for planning a change, not for current repository truth.
- Worklogs, daily notes, temp logs, project briefs, and scratch notes are local or historical records only.

#### Allowed responsibilities

- Planning and historical artifacts MAY:
  - explain why a change was proposed,
  - capture migration rationale,
  - record implementation progress,
  - provide historical context for a now-canonical spec.

#### Explicit non-responsibilities

- Planning artifacts MUST NOT be treated as the current authoritative contract.
- Worklogs and temp logs MUST NOT be treated as normative architecture references.
- A project brief or draft design MUST NOT override an accepted/current spec.

#### Inputs / outputs / contracts

- Inputs:
  - change proposals
  - design notes
  - task lists
  - daily notes
  - worklogs
  - temp logs
  - project briefs
- Outputs:
  - rationale
  - history
  - implementation checkpoints
  - future work items

#### Invariants

- Planning artifacts may become authoritative only after promotion into accepted/current specs.
- Historical notes may be referenced for context, but not for current truth.
- Non-normative artifacts must never silently outrank canonical specs.

#### Cross-module dependencies

- All planning artifacts should point back to accepted/current specs once those specs exist.
- Worklogs and daily notes should be treated as memory aids for local workflow continuity, not as repo architecture policy.

#### Failure modes if this boundary is violated

- An unaccepted draft is mistaken for canonical architecture.
- A temp log or project brief is used to justify code changes that contradict the accepted spec.
- Historical notes accumulate contradictory truths that future maintainers cannot reconcile.

#### Migration notes from current implementation

- AlphaForge keeps local worklogs and daily notes in the repo for continuity, and it also keeps OpenSpec proposals and tasks in the tree.
- Those artifacts are useful, but the hierarchy must make clear that they are planning or historical, not canonical.

#### Open questions / deferred decisions

- Whether project briefs should be archived alongside change artifacts or treated entirely as local working docs is deferred.
  - Recommended default: keep them advisory and historical unless they are explicitly promoted into OpenSpec.

#### Scenario: a temp log cannot override a canonical spec

- GIVEN a temp log describes a boundary differently from an accepted/current spec
- WHEN the discrepancy is discovered
- THEN the temp log SHALL be treated as non-normative history
- AND the accepted/current spec SHALL remain authoritative

### Requirement: conflicts are resolved by the accepted/current spec first, then implementation alignment, then derived documentation updates

When documentation layers disagree, AlphaForge SHALL resolve the conflict by applying the canonical hierarchy in order and then updating lower layers to match.

#### Purpose

- Give maintainers a procedural rule for resolving drift.
- Prevent “most recent file wins” or “most detailed comment wins” behavior from replacing canonical truth.

#### Canonical owner

- Accepted/current OpenSpec specs are the conflict-resolution anchor.
- Runtime code is the alignment target when it disagrees with a covered contract.
- Tests, README, docstrings, help text, and planning artifacts are update targets after the canonical spec is settled.

#### Allowed responsibilities

- Maintainers MAY:
  - update the accepted/current spec when the intended contract changes,
  - update implementation to match the spec when code drifts,
  - update tests after the contract is clarified,
  - update README and docs after the contract changes.

#### Explicit non-responsibilities

- No lower-authority artifact MAY resolve a contract conflict by itself.
- A README, test, docstring, or temp log MUST NOT be used to justify an architecture change that contradicts the accepted/current spec without an explicit spec update.

#### Inputs / outputs / contracts

- Inputs:
  - the conflicting artifacts
  - the accepted/current spec
  - implementation state
  - tests
  - user-facing docs
- Outputs:
  - a clear canonical interpretation
  - implementation alignment work
  - updated derived docs

#### Invariants

- Contract changes start at the spec layer.
- Implementation changes follow the accepted/current spec unless the change intentionally updates the spec and implementation together.
- Derived docs are synchronized after the canonical layer is settled.

#### Cross-module dependencies

- Runtime modules, tests, and docs all depend on the accepted/current specs for their canonical meaning.
- README and docstrings should reference canonical specs when they describe boundaries that may drift.

#### Failure modes if this boundary is violated

- Maintainers patch README instead of fixing a broken contract.
- Code, tests, and docs each tell a different story about ownership.
- The repo accumulates “almost canonical” explanations that nobody can safely trust.

#### Migration notes from current implementation

- AlphaForge already has several accepted/current contract specs that formalize behavior previously implied in code and docs.
- This hierarchy gives future changes a consistent order: change the spec first when the contract changes, then bring implementation, tests, and docs into alignment.

#### Open questions / deferred decisions

- Whether some low-level implementation details should ever be documented only in code comments and never in OpenSpec is deferred.
  - Recommended default: yes, for purely local implementation detail; no, for anything that affects cross-module ownership or contract behavior.

#### Scenario: the canonical spec wins when sources disagree

- GIVEN an accepted/current OpenSpec spec, a README, and a test comment disagree about module ownership
- WHEN a maintainer resolves the conflict
- THEN the accepted/current OpenSpec spec SHALL decide the contract truth
- AND the README, test, and comment SHALL be updated to match

