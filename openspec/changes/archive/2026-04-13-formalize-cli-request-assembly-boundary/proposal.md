# Proposal: formalize-cli-request-assembly-boundary

## Boundary problem

- `src/alphaforge/cli.py` currently parses arguments, assembles request DTOs, dispatches workflows, and formats user-facing JSON output.
- The CLI also touches report paths, storage refs, and adapter-specific fetch flows, which makes it easy for request assembly to blur into business ownership or path ownership.
- The repo has already frozen execution, market-data, persistence, and report-view-model boundaries, but the CLI boundary itself is still implicit.

## Canonical ownership decision

- `src/alphaforge/cli.py` becomes the canonical owner of CLI argument parsing, request-shape assembly, workflow dispatch, and terminal output formatting.
- `src/alphaforge/experiment_runner.py` remains the orchestration owner for workflow execution semantics.
- `src/alphaforge/storage.py` remains the owner of canonical artifact paths and layout.
- `src/alphaforge/report.py` remains the owner of report-view-model semantics.
- `src/alphaforge.data_loader.py` remains the owner of market-data acceptance semantics.

## Scope

- Subcommand parsing for `run`, `search`, `validate-search`, `walk-forward`, `fetch-twse`, and `twse-search`.
- Translation from `argv` into request DTOs such as `DataSpec`, `BacktestConfig`, `StrategySpec`, `ValidationSplitConfig`, `WalkForwardConfig`, and adapter request bundles.
- Dispatch into the correct orchestration or adapter entrypoint.
- Presentation of command output as derived JSON or text.

## Migration risk

- If CLI keeps duplicating domain validation, the same invocation can fail differently in the parser, runner, or downstream owner.
- If CLI keeps guessing artifact paths, command payloads can drift away from storage truth.
- If CLI keeps building report-facing payloads directly, report semantics can become split between CLI and report modules.

## Acceptance conditions

- CLI request assembly is limited to typed request construction and dispatch.
- Argument-level validation and semantic/domain validation are clearly separated.
- CLI output is derived from authoritative upstream return values, not from hidden local business rules.
- Combined commands like `twse-search` still preserve the storage, market-data, and report ownership boundaries.
