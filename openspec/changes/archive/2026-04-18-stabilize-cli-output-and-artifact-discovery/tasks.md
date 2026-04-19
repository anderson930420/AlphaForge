# Tasks

## 1. Spec and contract alignment

- [x] 1.1 Update the proposal and CLI discovery spec to name `src/alphaforge/cli.py` as the canonical owner of command-facing artifact discovery payloads.
- [x] 1.2 Spell out the required canonical artifact refs versus optional presentation refs for `run`, `search`, `validate-search`, and `walk-forward`.
- [x] 1.3 Document that validation search must surface the persisted summary path explicitly rather than leaving it implicit.

## 2. Code migration

- [x] 2.1 Update `cli.py` to keep the current stable payload fields while surfacing the missing validation summary discovery ref.
- [x] 2.2 Thread any needed explicit validation discovery output through the existing runner path without changing runtime or persistence ownership.
- [x] 2.3 Preserve optional report-path behavior for single/search flows without rebuilding report layout in CLI.
- [x] 2.4 Update README/help text wording only where it describes the stable CLI-facing discovery keys.

## 3. Verification

- [x] 3.1 Add or update tests that assert the CLI surfaces the canonical persisted refs for each workflow command.
- [x] 3.2 Add or update tests that assert optional presentation/report refs remain optional and are omitted when not generated.
- [x] 3.3 Add or update tests that lock the validation summary discovery path so users do not need to infer it from output layout.

## 4. Cleanup

- [x] 4.1 Remove any stale CLI wording that implies users must infer artifact locations from implementation details.
- [x] 4.2 Update the local worklog and Obsidian notes for the CLI discovery contract milestone.
