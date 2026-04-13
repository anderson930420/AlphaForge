# Delta for CLI Request Assembly Boundary

## ADDED Requirements

### Requirement: `cli.py` is the canonical owner of CLI request assembly and workflow dispatch

`src/alphaforge/cli.py` SHALL be the single authoritative owner of AlphaForge CLI argument parsing, command surface definition, request-shape assembly, workflow dispatch selection, and terminal output formatting.

#### Purpose

- Keep the CLI as the interface boundary for user requests instead of a second owner of business semantics.
- Make it explicit which parts of user input are syntax handling versus which parts are domain decisions owned upstream.
- Prevent command helpers, convenience payloads, and adapter shortcuts from becoming parallel canonical contracts.

#### Canonical owner

- `src/alphaforge/cli.py` is the only authoritative owner of:
  - subcommand parsing,
  - flag and option interpretation,
  - request DTO assembly from `argv`,
  - workflow dispatch selection,
  - CLI-facing output formatting.
- `src/alphaforge/experiment_runner.py` remains the authoritative owner of workflow orchestration behavior.
- `src/alphaforge/storage.py` remains the authoritative owner of canonical artifact paths and layout.
- `src/alphaforge/report.py` remains the authoritative owner of report-view-model semantics.
- `src/alphaforge.data_loader.py`, `src/alphaforge/backtest.py`, `src/alphaforge.metrics.py`, `src/alphaforge.benchmark.py`, `src/alphaforge.search.py`, and `src/alphaforge.strategy/*` remain the authoritative owners of their respective domain semantics.
- `src/alphaforge.twse_client.py` remains the authoritative owner of TWSE adapter normalization.

#### Allowed responsibilities

- `cli.py` MAY:
  - define the user-facing subcommand surface,
  - parse strings, numbers, booleans, lists, and paths from `argv`,
  - convert parsed values into request DTOs such as `DataSpec`, `BacktestConfig`, `StrategySpec`, `ValidationSplitConfig`, `WalkForwardConfig`, and adapter request bundles,
  - choose which orchestration or adapter entrypoint to call for each subcommand,
  - call a composite sequence when the CLI surface explicitly exposes a composite command,
  - print derived JSON or text payloads based on authoritative upstream return values,
  - surface storage refs, report refs, and workflow summaries that were returned by upstream owners.

#### Explicit non-responsibilities

- `cli.py` MUST NOT own execution semantics, market-data acceptance semantics, metrics semantics, benchmark semantics, report-view-model semantics, or persisted artifact layout.
- `cli.py` MUST NOT define canonical path truth, canonical report-input truth, or canonical market-data schema truth.
- `cli.py` MUST NOT become the source of business-rule validation for search windows, split ratios, strategy signals, trade extraction, or benchmark formulas.
- `cli.py` MUST NOT infer storage filenames or directory structure on its own.
- `cli.py` MUST NOT turn user-facing convenience payloads into new canonical schemas.

#### Inputs / outputs / contracts

- Inputs:
  - `argv`
  - environment or config-backed defaults exposed through `config.py`
  - explicit subcommand options and flags
- Request DTOs CLI MAY assemble:
  - `DataSpec`
  - `BacktestConfig`
  - `StrategySpec`
  - `ValidationSplitConfig`
  - `WalkForwardConfig`
  - search parameter grids
  - adapter transport requests such as `TwseFetchRequest`
- Outputs:
  - dispatched workflow calls to `experiment_runner.py` or adapter entrypoints
  - user-facing JSON or text payloads
  - surfaced artifact refs and summary paths that were returned by upstream owners
- CLI output contract:
  - command output is presentation-only and derived from authoritative runtime, storage, and report owners
  - CLI may rename fields for display, but it may not redefine their business meaning

#### Invariants

- CLI request assembly preserves the meaning of upstream DTO fields instead of inventing new semantics.
- CLI dispatch is selection-only: it chooses the correct entrypoint, then downstream owners define the workflow behavior.
- CLI-facing output can be richer or slimmer than the underlying runtime objects, but it must remain derived from authoritative results and refs.
- A CLI convenience flow such as `twse-search` does not change the canonical ownership of market-data acceptance, storage layout, or report semantics.

#### Cross-module dependencies

- `experiment_runner.py` receives request DTOs from `cli.py` and performs workflow orchestration.
- `storage.py` provides canonical artifact refs and path values that CLI may display.
- `report.py` provides report-input semantics and report renderers; CLI may trigger them, but it does not define them.
- `twse_client.py` provides adapter request and fetch behavior for TWSE flows.
- `config.py` may provide defaults and static ranges used during parsing, but not business ownership.

#### Failure modes if this boundary is violated

- The same CLI invocation can be accepted by the parser but rejected by downstream owners for a different reason because validation rules are duplicated.
- Search, validation, or walk-forward commands can drift because CLI starts encoding workflow semantics locally.
- Command output can advertise paths that storage never wrote because CLI guessed the layout.
- Report-related JSON fields can become a second report schema if CLI starts reshaping them independently.
- Adapter-specific commands can bypass canonical market-data acceptance if CLI treats transport convenience as business authority.

#### Migration notes from current implementation

- `cli.py` already builds `DataSpec`, `BacktestConfig`, `StrategySpec`, and parameter grids from parsed arguments.
- `cli.py` already dispatches `run`, `search`, `validate-search`, `walk-forward`, `fetch-twse`, and `twse-search`.
- `cli.py` currently formats JSON payloads that include serialized results, artifact refs, and report paths.
- `cli.py` currently performs a direct report rendering path for `run --generate-report`, which makes the report boundary easy to blur if the report input contract is not explicit.
- `twse-search` currently combines adapter fetch, data save, and search dispatch in one command, so the CLI must stay careful not to absorb TWSE normalization or storage ownership.

#### Open questions / deferred decisions

- Whether `cli.py` should eventually move some presentation helpers into a dedicated output-format module is deferred.
  - Recommended default: keep CLI formatting local until the output contract becomes more complex than request assembly plus derived JSON payloads.
- Whether `run --generate-report` should dispatch report generation through `experiment_runner.py` or continue to call report helpers directly is deferred.
  - Recommended default: keep the report input owner in `report.py` and let CLI only initiate rendering.
- Whether adapter convenience commands should remain in the CLI surface long term is deferred.
  - Recommended default: keep them if they remain thin transport composites and do not become domain owners.

#### Scenario: CLI parses and dispatches without owning domain semantics

- GIVEN a user invokes `alphaforge run --data sample.csv --short-window 5 --long-window 20`
- WHEN `cli.py` parses the command
- THEN it SHALL assemble the request DTOs needed for downstream execution
- AND it SHALL NOT decide the execution timing, market-data acceptance, or metric formulas itself

#### Scenario: CLI output is derived from authoritative upstream refs

- GIVEN a workflow returns artifact references and result summaries
- WHEN `cli.py` formats the terminal payload
- THEN it SHALL print those derived refs and summaries
- AND it SHALL NOT infer new canonical paths or report semantics locally

### Requirement: CLI argument validation is syntactic only; domain validation stays upstream

`src/alphaforge/cli.py` SHALL perform only syntactic and request-shape validation, while semantic validation of business rules SHALL remain owned by the authoritative upstream modules.

#### Purpose

- Keep parser errors and business-rule errors distinguishable.
- Prevent the CLI from becoming a second validation layer for market data, execution, search, report, or storage semantics.

#### Canonical owner

- `cli.py` is the authoritative owner of syntactic argument validation.
- `data_loader.py`, `backtest.py`, `metrics.py`, `benchmark.py`, `search.py`, `report.py`, and `storage.py` remain authoritative for their own semantic validations.
- `experiment_runner.py` remains the orchestration layer that calls those owners in the correct order.

#### Allowed responsibilities

- `cli.py` MAY:
  - require subcommand arguments to be present,
  - parse integers, floats, paths, strings, and boolean flags,
  - reject malformed CLI combinations that cannot even form a request DTO,
  - normalize argument names into typed request fields,
  - raise parser-level errors for unknown commands or invalid option shapes.

#### Explicit non-responsibilities

- `cli.py` MUST NOT decide whether market data is canonical or acceptable.
- `cli.py` MUST NOT decide whether a strategy parameter combination is valid for execution.
- `cli.py` MUST NOT decide whether a split ratio, train size, or window combination is semantically valid.
- `cli.py` MUST NOT decide whether benchmark or metric values are correct.
- `cli.py` MUST NOT validate report inputs beyond ensuring the CLI can dispatch the request shape.

#### Inputs / outputs / contracts

- Syntactic validation inputs:
  - parsed argv
  - option types and required flags
- Semantic validation inputs:
  - loader-accepted market data
  - strategy specs
  - backtest configs
  - report inputs
  - storage outputs
- CLI may reject:
  - missing required arguments,
  - malformed types,
  - impossible command shapes,
  - command combinations that cannot produce a request DTO
- CLI must defer:
  - invalid market-data content,
  - invalid strategy semantics,
  - invalid execution semantics,
  - invalid report-field meaning,
  - invalid persistence layout assumptions

#### Invariants

- Any error raised by CLI parsing should be attributable to request-shape or syntax failure, not to hidden domain logic.
- If a request is syntactically valid but semantically invalid, the authoritative upstream owner must raise the error.
- The same semantic rule must not be implemented in both CLI and the upstream owner as a hidden fallback.

#### Cross-module dependencies

- `config.py` may provide default values and ranges used to populate parser defaults.
- `data_loader.py` owns market-data acceptance checks.
- `search.py` owns search-space validity.
- `backtest.py` owns execution semantics that make some combinations invalid.
- `report.py` owns report-input completeness checks.

#### Failure modes if this boundary is violated

- Users see different error messages for the same invalid input depending on which path they used.
- CLI tests begin duplicating domain assertions that belong in upstream owners.
- Invalid business inputs can be rejected too early or too late, making debugging harder.
- Parser-only issues get conflated with genuine market-data or execution problems.

#### Migration notes from current implementation

- `cli.py` already delegates type conversion to `argparse` and constructs typed DTOs from parsed values.
- The current CLI also performs command-level branching for `generate-report`, `fetch-twse`, and `twse-search`, which is acceptable only if the branch stays syntactic and dispatch-oriented.
- Some of the current command output is built from serialized runtime objects, which is correct as long as the CLI does not reinterpret those objects as its own truth.

#### Open questions / deferred decisions

- Whether CLI should expose a shared helper for parser-level validation errors versus using `argparse` defaults directly is deferred.
  - Recommended default: keep parser validation in `argparse` and reserve custom checks for request-shape cases that `argparse` cannot express.
- Whether a future CLI command should be allowed to perform nontrivial preflight checks before dispatch is deferred.
  - Recommended default: only if the check is syntax-level; otherwise let the authoritative owner validate.

#### Scenario: parser errors stay distinct from domain errors

- GIVEN a user omits a required CLI flag
- WHEN `cli.py` parses the command
- THEN it SHALL reject the invocation as a request-shape failure
- AND it SHALL NOT masquerade as a market-data, execution, or storage error

### Requirement: CLI output is derived presentation, not canonical storage or report truth

CLI-facing output in AlphaForge SHALL be treated as a derived presentation contract that surfaces authoritative runtime, storage, and report results without redefining them.

#### Purpose

- Keep terminal output useful while preventing command payloads from becoming new source-of-truth schemas.
- Preserve the separation between user-facing labels and canonical module-owned facts.

#### Canonical owner

- `cli.py` is the authoritative owner of command-facing output formatting.
- `storage.py` remains authoritative for canonical artifact refs and layout.
- `report.py` remains authoritative for report content and report input semantics.
- `experiment_runner.py` remains authoritative for workflow result objects.

#### Allowed responsibilities

- `cli.py` MAY:
  - serialize runtime results into JSON or text,
  - include storage refs and report refs that were returned by upstream owners,
  - rename fields for presentation, provided the meaning remains unchanged,
  - surface workflow summary objects and counts,
  - include display-only labels for user convenience.

#### Explicit non-responsibilities

- `cli.py` MUST NOT invent canonical artifact paths.
- `cli.py` MUST NOT invent canonical report-input semantics.
- `cli.py` MUST NOT invent new persistence fields that storage did not return.
- `cli.py` MUST NOT replace authoritative runtime fields with local summary approximations.

#### Inputs / outputs / contracts

- CLI output may include:
  - serialized `ExperimentResult`, `ValidationResult`, and `WalkForwardResult`
  - storage refs such as artifact paths or summary files
  - report refs such as generated report paths
  - display-only status fields like result counts or command labels
- CLI output must remain downstream of authoritative owners and must not be treated as the canonical schema for storage or reporting.

#### Invariants

- A displayed path is only a presentation of a path already owned elsewhere.
- A displayed summary is only a derivation of upstream data already computed elsewhere.
- CLI output may be richer than the underlying runtime object, but it may not be more authoritative than the owner that created the underlying fact.

#### Cross-module dependencies

- `storage.py` supplies canonical refs.
- `report.py` supplies report refs and report content when generated.
- `experiment_runner.py` supplies workflow results.
- `twse_client.py` may supply fetch result data that CLI surfaces in adapter commands.

#### Failure modes if this boundary is violated

- A CLI summary becomes a second schema owner and drifts from runtime or storage truth.
- Users copy a printed path that never existed because CLI guessed layout instead of using returned refs.
- Report-related CLI fields start competing with report-view-model semantics.
- Terminal output and persisted artifacts disagree because the CLI introduced its own summary logic.

#### Migration notes from current implementation

- `cli.py` currently prints JSON payloads that combine serialized results, storage refs, and report paths.
- `cli.py` currently emits search summaries such as top results and report-related refs.
- That behavior is acceptable only if the payload is clearly derived from authoritative upstream owners and not treated as a canonical schema of its own.

#### Open questions / deferred decisions

- Whether CLI should eventually expose a dedicated structured output model for machine consumers is deferred.
  - Recommended default: keep the current command-facing JSON as derived presentation only unless a separate machine API becomes necessary.

#### Scenario: CLI summaries remain derived

- GIVEN a search command returns ranked results and report refs
- WHEN `cli.py` prints the payload
- THEN the payload SHALL be derived from upstream owners
- AND it SHALL NOT become the canonical owner of rankings, paths, or report semantics

### Requirement: CLI adapter commands are transport-level composites, not alternate market-data authorities

CLI commands that talk to adapters, including TWSE flows, SHALL remain transport-level composites and SHALL NOT change canonical market-data ownership.

#### Purpose

- Allow convenience commands like fetch-and-search without letting the CLI absorb adapter semantics.
- Keep source-specific transport logic separate from canonical market-data acceptance and downstream execution.

#### Canonical owner

- `cli.py` is the authoritative owner of the CLI surface for adapter commands.
- `twse_client.py` is the authoritative owner of TWSE payload normalization and fetch behavior.
- `data_loader.py` remains the authoritative owner of canonical market-data acceptance.

#### Allowed responsibilities

- `cli.py` MAY:
  - select source-specific adapter commands,
  - construct adapter transport requests such as `TwseFetchRequest`,
  - call adapter fetch functions,
  - save adapter-produced files through adapter or storage-owned helpers if those helpers are already exposed,
  - chain fetch and search steps when the user explicitly invoked a composite command.

#### Explicit non-responsibilities

- `cli.py` MUST NOT redefine TWSE normalization semantics.
- `cli.py` MUST NOT define canonical market-data column rules or acceptance policy.
- `cli.py` MUST NOT treat adapter convenience paths as canonical acceptance paths.
- `cli.py` MUST NOT bypass `data_loader.py` when downstream workflows require accepted market data.

#### Inputs / outputs / contracts

- Adapter-flow inputs:
  - stock identifier or source-specific identifier
  - source date/month range
  - adapter request DTOs
- Adapter-flow outputs:
  - fetched payloads or saved files
  - downstream request DTOs that point at those saved files
  - search or execution dispatch after the adapter step completes

#### Invariants

- Adapter-specific CLI commands may be composite, but each composite step still preserves the canonical owner of its own semantics.
- A composite command does not change which module owns market-data acceptance or storage layout.
- Transport convenience never upgrades the CLI into a source-data authority.

#### Cross-module dependencies

- `twse_client.py` handles TWSE request translation and payload normalization.
- `data_loader.py` accepts the resulting market-data frame before general downstream use.
- `experiment_runner.py` receives the post-CLI request DTOs for search or execution workflows.

#### Failure modes if this boundary is violated

- TWSE-specific CLI behavior starts diverging from canonical CSV-based workflows.
- Adapter commands skip canonical acceptance and create hidden schema drift.
- Convenience fetch paths become pseudo-canonical and later break general workflows.

#### Migration notes from current implementation

- `cli.py` currently lazily imports `twse_client.py` and constructs `TwseFetchRequest` for fetch and twse-search commands.
- `twse-search` currently chains fetch, save, and search in one user command, which is acceptable only if the adapter and storage owners remain authoritative for their own steps.
- The CLI should keep those commands as transport composites, not as a place to reinterpret TWSE or market-data semantics.

#### Open questions / deferred decisions

- Whether TWSE fetch-and-search should stay a first-class CLI composite or be split into separate commands later is deferred.
  - Recommended default: keep the composite if it remains a thin transport wrapper over authoritative owners.

#### Scenario: adapter command remains transport-only

- GIVEN a user invokes `alphaforge twse-search`
- WHEN `cli.py` assembles the request
- THEN it SHALL build the adapter request and dispatch the downstream workflow
- AND it SHALL NOT redefine TWSE normalization or canonical market-data acceptance

