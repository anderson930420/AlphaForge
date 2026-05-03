# Tasks

## 1. Spec and contract alignment

- [ ] 1.1 Add the custom-signal boundary spec and update the surrounding canonical specs for registry, search, execution, research-validation, CLI, and architecture ownership.
- [ ] 1.2 Validate the OpenSpec change before runtime implementation.

## 2. Code migration

- [ ] 2.1 Add the custom-signal validation and target-position derivation module.
- [ ] 2.2 Register `custom_signal` in the strategy registry without moving signal parsing or signal-value computation into the registry.
- [ ] 2.3 Wire `research-validate` CLI and runner workflows to accept `--signal-file` and pass validated target positions into execution.
- [ ] 2.4 Ensure search-space generation rejects `custom_signal` as validation-only.
- [ ] 2.5 Preserve the existing execution semantics and avoid introducing a second execution model.

## 3. Verification

- [ ] 3.1 Add tests for valid signal files, missing required columns, binary validation, date alignment, duplicate detection, missing dates, and `signal_value` being ignored.
- [ ] 3.2 Add tests for CLI request assembly, registry dispatch, search rejection, and research-validation orchestration.
- [ ] 3.3 Run targeted tests, OpenSpec validation, and full pytest.

## 4. Cleanup

- [ ] 4.1 Remove any stale signal parsing, signal-value computation, or duplicate validation outside the new custom-signal boundary.
- [ ] 4.2 Log implementation steps through the local Obsidian workflow.
