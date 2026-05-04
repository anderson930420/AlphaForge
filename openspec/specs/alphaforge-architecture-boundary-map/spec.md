# AlphaForge Architecture Boundary Map Specification

## Purpose

- Define the authoritative boundary map for AlphaForge so every business rule, execution semantic, schema, naming convention, and workflow responsibility has exactly one canonical owner.
- Serve as the top-level contract for assigning modules to one of three roles only: contract layer, implementation layer, or orchestration layer.
- Prevent business-rule drift between `config.py`, `schemas.py`, `storage.py`, `report.py`, `cli.py`, and `experiment_runner.py`.
- Prevent future feature additions from turning `experiment_runner.py` or `cli.py` into modules that silently own domain rules.
## Requirements
### Requirement: AlphaForge modules shall have exactly one canonical owner per boundary

AlphaForge SHALL assign each business rule, execution semantic, schema, naming convention, and workflow responsibility to exactly one canonical owner, with lower-level capability specs allowed to refine but not contradict the top-level map.

#### Scenario: Boundary ownership remains single-sourced

- **WHEN** a maintainer looks up the owner for market data, execution, persistence, reporting, CLI dispatch, or orchestration
- **THEN** the architecture boundary map SHALL provide a single canonical answer
- **AND** lower-level specs SHALL only refine that answer, not create a competing one

### Requirement: `metrics.py` owns excess-return Sharpe semantics with a per-period risk-free input

`src/alphaforge/metrics.py` SHALL remain the canonical owner of Sharpe-ratio semantics, including subtraction of a caller-supplied per-period `risk_free_rate` before annualization.

#### Purpose

- Keep performance analytics semantics centralized in `metrics.py`.
- Make it explicit that Sharpe uses excess per-period returns while preserving backward compatibility for existing callers.

#### Canonical owner

- `src/alphaforge/metrics.py` is the authoritative owner of Sharpe-ratio calculation semantics.
- `src/alphaforge/runner_workflows.py`, `src/alphaforge/permutation.py`, `src/alphaforge/report.py`, `src/alphaforge/storage.py`, and `src/alphaforge/cli.py` are downstream consumers of the computed metric values only.

#### Allowed responsibilities

- `metrics.py` MAY accept `risk_free_rate: float = 0.0` on `compute_metrics()` and `_compute_sharpe_ratio()`.
- `metrics.py` MAY interpret `risk_free_rate` as a per-period rate matching the return frequency in `strategy_return`.
- `metrics.py` MAY preserve the current output schema by leaving `MetricReport` field names unchanged.

#### Explicit non-responsibilities

- `BacktestConfig` MUST NOT become the owner of risk-free-rate configuration in this change.
- `report.py`, `storage.py`, and `cli.py` MUST NOT recompute Sharpe by applying a separate risk-free adjustment locally.

#### Inputs / outputs / contracts

- Inputs:
  - per-period `strategy_return` series
  - `annualization_factor`
  - optional per-period `risk_free_rate`
- Output:
  - `MetricReport.sharpe_ratio`
- Contract rules:
  - the caller is responsible for converting any annual risk-free assumption into the matching per-period rate before calling `metrics.py`
  - omitting `risk_free_rate` preserves the previous raw-return behavior through the default `0.0`

#### Invariants

- Sharpe semantics have one authoritative implementation.
- Backward compatibility is preserved for callers that do not pass `risk_free_rate`.

### Requirement: `custom_signal.py` owns external signal-file validation and target-position derivation

`src/alphaforge/custom_signal.py` SHALL be the canonical owner of validating externally supplied `signal.csv` files and deriving `target_position` values for the `custom_signal` workflow.

#### Scenario: custom signal validation has one canonical owner

- GIVEN AlphaForge consumes an external `signal.csv`
- WHEN the `custom_signal` workflow validates the file
- THEN `custom_signal.py` SHALL own the validation and target-position derivation
- AND no other module SHALL redefine the signal-file contract or binary-to-target mapping

### Requirement: AlphaForge is a validation engine, not the alpha-generation platform

AlphaForge SHALL be documented and treated as a spec-driven quant research validation engine and SHALL NOT be positioned as the primary alpha-generation platform.

#### Scenario: AlphaForge boundary statements remain validation-focused

- GIVEN future documentation or canonical boundary text describes AlphaForge
- WHEN it states the repo's purpose
- THEN it SHALL describe AlphaForge as a validation layer for OHLCV research, backtesting, diagnostics, and externally generated signals
- AND it SHALL NOT claim AlphaForge is the signal-generation owner

#### Scenario: SignalForge remains the alpha-generation owner

- GIVEN a signal package is produced for AlphaForge
- WHEN the package handoff is described
- THEN SignalForge SHALL be the signal-generation owner
- AND AlphaForge SHALL remain the validator and backtester of that exported signal package

### Requirement: focused research evidence diagnostics have a single owner

AlphaForge SHALL assign cost-sensitivity and bootstrap-evidence formulas to a focused diagnostics module rather than to `backtest.py`, `storage.py`, or `report.py`.

#### Scenario: diagnostics remain outside the execution owner

- GIVEN research evidence diagnostics are computed
- WHEN ownership is assigned
- THEN `src/alphaforge/evidence_diagnostics.py` SHALL be the canonical owner of the diagnostic formulas
- AND `backtest.py` SHALL remain execution semantics only
- AND `storage.py` and `report.py` SHALL remain serializer / presentation consumers only

### Requirement: research-validation orchestration remains orchestration only

`runner_workflows.py` SHALL orchestrate minimal evidence diagnostics as part of research validation but SHALL NOT own the diagnostic formulas or evidence semantics.

#### Scenario: workflow remains a coordinator

- GIVEN a research-validation workflow produces diagnostics
- WHEN the architecture map is consulted
- THEN `runner_workflows.py` SHALL be described as orchestration only
- AND the diagnostics module SHALL own the formulas

## Canonical owner

- This specification file is the authoritative top-level boundary definition for AlphaForge architecture.
- `openspec/specs/alphaforge-architecture-boundary-map/spec.md` is the only authoritative source for:
  - major layer definitions,
  - canonical-truth ownership assignments,
  - module classification as contract-only, implementation-only, orchestration-only, persistence-only, presentation-only, adapter-only, or repo-tooling-only,
  - forbidden ownership for each major layer.
- Lower-level capability specs may refine a boundary defined here, but they must not contradict the canonical owner assignments in this document.

## Allowed responsibilities

### A. Layer map

- Contract layer:
  - `src/alphaforge/schemas.py` is the authoritative owner of in-memory runtime contracts and shared typed result structures.
  - `src/alphaforge/strategy/base.py` is the authoritative owner of the strategy interface contract.
- Configuration layer:
  - `src/alphaforge/config.py` is authoritative only for static defaults, parameter ranges, and runtime-independent constants.
- Domain implementation layer:
  - `src/alphaforge/data_loader.py` is authoritative for canonical market data schema enforcement after raw data is available locally.
  - `src/alphaforge/strategy/ma_crossover.py` is implementation-only for the MA crossover strategy logic.
  - `src/alphaforge/strategy/breakout.py` is implementation-only for the breakout strategy logic.
  - `src/alphaforge/backtest.py` is authoritative for execution semantics.
  - `src/alphaforge/metrics.py` is authoritative for performance analytics semantics.
  - `src/alphaforge/benchmark.py` is authoritative for benchmark semantics.
  - `src/alphaforge/search.py` is authoritative for search-space generation rules.
  - `src/alphaforge/policy.py` is authoritative for post-search candidate promotion/rejection policy evaluation.
- External adapter layer:
  - `src/alphaforge/twse_client.py` is authoritative for external TWSE payload normalization into AlphaForge market-data shape before the generic loader validates it.
- Presentation layer:
  - `src/alphaforge/visualization.py` is authoritative for figure generation and presentation-only visual transforms.
  - `src/alphaforge/report.py` is authoritative for report rendering from already-computed artifacts.
- Persistence layer:
  - `src/alphaforge/storage.py` is authoritative for persisted artifact schemas, artifact naming, and output directory layout.
- Orchestration layer:
  - `src/alphaforge/experiment_runner.py` is orchestration-only as the public runner façade and compatibility surface.
  - `src/alphaforge/runner_workflows.py` is orchestration-only for workflow-specific runner sequencing.
  - `src/alphaforge/runner_protocols.py` is orchestration-only for shared runner-only helper logic.
  - `src/alphaforge/cli.py` is orchestration-only for CLI request assembly and process-level command dispatch.
- Documentation layer:
  - `PROJECT_BRIEF.md`, `README.md`, and module docstrings are advisory-only descriptions of the intended architecture and user-facing behavior.
- Repo tooling layer:
  - `src/obsidian_logger.py` and `scripts/read_memory.py` are authoritative only for developer workflow support on this machine and are outside the AlphaForge product runtime boundary.

### B. Canonical truth table

| Canonical truth category | Authoritative owner | Layer role | Non-authoritative consumers |
| --- | --- | --- | --- |
| Canonical market data schema | `src/alphaforge/data_loader.py` | contract-enforcement + implementation | `twse_client.py`, `backtest.py`, `visualization.py`, `report.py` |
| Strategy interface contract | `src/alphaforge/strategy/base.py` | contract-only | `strategy/ma_crossover.py`, `strategy/breakout.py`, `experiment_runner.py` |
| Strategy implementation families | `src/alphaforge/strategy/ma_crossover.py`, `src/alphaforge/strategy/breakout.py` | implementation-only | `experiment_runner.py`, `search.py` |
| Execution semantics | `src/alphaforge/backtest.py` | implementation-authoritative | `metrics.py`, `report.py`, `storage.py`, `cli.py` |
| Search-space generation | `src/alphaforge/search.py` | implementation-authoritative | `cli.py`, `experiment_runner.py` |
| Post-search candidate promotion/rejection policy | `src/alphaforge/policy.py` | implementation-authoritative | `experiment_runner.py`, `storage.py`, `cli.py` |
| Public runner facade | `src/alphaforge/experiment_runner.py` | orchestration-only | `cli.py` |
| Search execution | `src/alphaforge/runner_workflows.py` | orchestration-only | `experiment_runner.py`, `cli.py` |
| Validation protocol | `src/alphaforge/runner_workflows.py` | orchestration-only | `experiment_runner.py`, `cli.py`, `storage.py` |
| Walk-forward protocol | `src/alphaforge/runner_workflows.py` | orchestration-only | `experiment_runner.py`, `cli.py`, `storage.py` |
| Runner shared protocol helpers | `src/alphaforge/runner_protocols.py` | orchestration-only | `runner_workflows.py` |
| Performance analytics semantics | `src/alphaforge/metrics.py` | implementation-authoritative | `scoring.py`, `report.py`, `storage.py` |
| Benchmark semantics | `src/alphaforge/benchmark.py` | implementation-authoritative | `report.py`, `experiment_runner.py` |
| visualization generation | `src/alphaforge/visualization.py` | presentation-only | `report.py` |
| Report rendering | `src/alphaforge/report.py` | presentation-authoritative | `cli.py`, `experiment_runner.py` |
| Report workflow orchestration | `src/alphaforge/experiment_runner.py` | orchestration-only | `cli.py` |
| In-memory result schemas | `src/alphaforge/schemas.py` | contract-only | all runtime modules |
| Persisted artifact schemas | `src/alphaforge/storage.py` | persistence-authoritative | `cli.py`, `report.py`, `experiment_runner.py`, `README.md` |
| Artifact naming and directory layout | `src/alphaforge/storage.py` | persistence-authoritative | `cli.py`, `README.md`, `report.py`, `experiment_runner.py` |
| CLI request assembly | `src/alphaforge/cli.py` | orchestration-only | none |
| external data adapter normalization | `src/alphaforge/twse_client.py` | adapter-authoritative | `cli.py`, `data_loader.py` |
| repo tooling / developer workflow support | `src/obsidian_logger.py`, `scripts/read_memory.py` | repo-tooling-only | `AGENTS.md` and local workflow only |

### C. Responsibility matrix

| Module | Classification | Allowed ownership |
| --- | --- | --- |
| `config.py` | configuration-only | defaults, parameter ranges, output root defaults, static loader constants |
| `schemas.py` | contract-only | dataclasses and typed result structures shared across runtime modules |
| `data_loader.py` | contract-enforcement + implementation | market-data column normalization, missing-data policy, schema validation for locally available OHLCV data |
| `twse_client.py` | adapter-only | remote fetch, remote payload parsing, adapter normalization into loader-consumable frame |
| `strategy/base.py` | contract-only | strategy construction and signal-generation interface |
| `strategy/ma_crossover.py` | implementation-only | MA parameter validation specific to MA strategy and MA signal generation |
| `strategy/breakout.py` | implementation-only | breakout parameter validation specific to breakout strategy and breakout signal generation |
| `backtest.py` | implementation-authoritative | target-position application, timing semantics, fee/slippage application, trade extraction, equity-curve construction |
| `metrics.py` | implementation-authoritative | return, drawdown, Sharpe, turnover, trade count, win rate semantics |
| `benchmark.py` | implementation-authoritative | buy-and-hold benchmark construction and benchmark summary semantics |
| `visualization.py` | presentation-only | chart building from already-computed data |
| `report.py` | presentation-authoritative | HTML assembly, report section composition, figure embedding, rendered report persistence |
| `search.py` | implementation-authoritative | parameter-grid expansion and strategy-spec generation |
| `policy.py` | implementation-authoritative | post-search candidate promotion/rejection policy evaluation |
| `permutation.py` | implementation-authoritative | fixed-candidate permutation/null-comparison diagnostic computation and target-metric selection |
| `experiment_runner.py` | orchestration-only | expose stable public runner entry points and compatibility bundles |
| `runner_workflows.py` | orchestration-only | sequence workflow-specific runtime steps, call authoritative owners, assemble workflow-level result objects |
| `runner_protocols.py` | orchestration-only | shared runner-only helpers for config resolution, strategy dispatch, split/fold generation, and workflow metadata assembly |
| `storage.py` | persistence-authoritative | disk schema, filenames, directory paths, JSON/CSV export shape, persisted summary type normalization |
| `cli.py` | orchestration-only | parse command requests, instantiate request contracts, dispatch workflows, print CLI payloads |
| `PROJECT_BRIEF.md`, `README.md`, docstrings | advisory-only | explain intended behavior; must not redefine authoritative runtime rules |
| `obsidian_logger.py`, `scripts/read_memory.py` | repo-tooling-only | local memory and logging workflow only |

## Explicit non-responsibilities

- `config.py` must not own runtime data schemas, persisted artifact schemas, execution semantics, or strategy interface semantics.
- `schemas.py` must not own directory layout, filename selection, missing-data policy, execution timing semantics, scoring formulas, or HTML layout.
- `data_loader.py` must not fetch remote data, score results, construct reports, define artifact filenames, or own strategy-specific parameter validation.
- `twse_client.py` must not own the canonical market data schema after loader validation, missing-data policy, search defaults, or storage layout.
- `strategy/base.py` must not own parameter ranges, ranking logic, execution timing, benchmark logic, or persistence.
- `strategy/ma_crossover.py` and `strategy/breakout.py` must not own search-space generation, backtest semantics, metrics semantics, or report-facing schema requirements.
- `backtest.py` must not own metric formulas, ranking formulas, report rendering, artifact naming, or parameter-grid generation.
- `metrics.py` must not own benchmark formulas, scoring thresholds, backtest timing, report formatting, or persisted JSON schema.
- `benchmark.py` must not own report text, figure construction, strategy metrics, or ranking.
- `visualization.py` must not compute authoritative metrics, mutate persisted artifacts, or decide report workflow ordering.
- `report.py` must not compute authoritative backtest metrics, define benchmark semantics, own artifact directory layout, or choose search-space rules.
- `search.py` must not run backtests, compute metrics, save artifacts, or decide validation or walk-forward scheduling.
- `policy.py` must not run backtests, generate candidates, save artifacts, or define report/view-model semantics.
- `permutation.py` must not generate candidates, decide promotion policy, or define report/view-model semantics.
- `experiment_runner.py`, `runner_workflows.py`, and `runner_protocols.py` must not redefine schemas already owned by `schemas.py` or `storage.py`, and must not embed business rules that belong to `backtest.py`, `metrics.py`, `benchmark.py`, `search.py`, or `data_loader.py`.
- `storage.py` must not compute metrics, decide ranking, generate figures, or decide validation protocol semantics.
- `cli.py` must not validate business rules beyond request-shape checks, and must not redefine workflow semantics that belong to `experiment_runner.py` or domain rules that belong elsewhere.
- `README.md`, `PROJECT_BRIEF.md`, and docstrings must not become the only place a runtime rule is defined.
- `obsidian_logger.py` and `scripts/read_memory.py` must not be imported into AlphaForge product runtime modules.

## Inputs / outputs / contracts

- Input contract for market data:
  - Raw adapter payloads may originate in `twse_client.py`.
  - Canonical runtime OHLCV acceptance is enforced by `data_loader.py`.
  - Required canonical columns after loader validation are `datetime`, `open`, `high`, `low`, `close`, `volume`.
- Input contract for strategies:
  - `schemas.StrategySpec` and `strategy.base.Strategy.generate_signals()` are authoritative for strategy invocation shape.
- Input contract for execution:
  - `schemas.BacktestConfig` is the authoritative in-memory configuration contract consumed by `backtest.py`.
- Output contract for in-memory workflow results:
  - `schemas.ExperimentResult`, `ValidationResult`, and `WalkForwardResult` are authoritative runtime result contracts.
- Output contract for persisted artifacts:
  - `storage.py` is authoritative for `experiment_config.json`, `metrics_summary.json`, `trade_log.csv`, `equity_curve.csv`, `ranked_results.csv`, `validation_summary.json`, `walk_forward_summary.json`, and `fold_results.csv`.
- Output contract for reports:
  - `report.py` is authoritative for rendered HTML strings and saved `.html` report files.
- CLI contract:
  - `cli.py` owns argparse argument shape and command payload assembly.
  - CLI JSON output is derived from authoritative runtime contracts in `schemas.py` and authoritative persistence paths from `storage.py`.

## Invariants

- Each canonical truth category listed in this spec has exactly one authoritative owner.
- Any duplicated validation rule must be labeled as either authoritative or advisory-only; advisory validation may reject obviously malformed inputs but must not redefine authoritative semantics.
- Any duplicated schema representation must be labeled as authoritative or derived; derived representations must be generated from the authoritative contract owner.
- `experiment_runner.py`, `runner_workflows.py`, `runner_protocols.py`, and `cli.py` remain orchestration-only; they must not encode domain rules already owned elsewhere.
- Persisted artifact naming and directory layout remain authoritative in `storage.py` even if README examples or CLI payloads display those paths.
- Documentation remains advisory-only and must be updated to match authoritative owners rather than define parallel truths.
- Repo tooling stays outside product runtime and must not alter AlphaForge domain behavior.

## Cross-module dependencies

- `twse_client.py` depends on external TWSE payload structure and produces a loader-consumable frame; `data_loader.py` is authoritative when adapter output conflicts with runtime schema expectations.
- `strategy/ma_crossover.py` and `strategy/breakout.py` depend on `StrategySpec` from `schemas.py` and the interface contract in `strategy/base.py`.
- `backtest.py` depends on canonical market-data columns validated by `data_loader.py` and on strategy outputs produced through the `Strategy` contract.
- `metrics.py` depends on the equity-curve and trade-log semantics emitted by `backtest.py`.
- `benchmark.py` depends on market-data close-price semantics but does not depend on backtest internals.
- `search.py` depends on `StrategySpec` contract shape from `schemas.py`.
- `policy.py` depends on evidence contracts from `schemas.py` and on workflow evidence assembled by the runner layer.
- `experiment_runner.py` depends on `runner_workflows.py` for internal implementation and remains downstream of authoritative domain owners.
- `runner_workflows.py` depends on all authoritative domain owners and on `runner_protocols.py`.
- `storage.py` depends on in-memory result contracts from `schemas.py` and on runtime outputs from `backtest.py`, `metrics.py`, and the runner layer.
- `visualization.py` depends on report-facing frame shapes and trade-log data, but those inputs are derived from authoritative runtime and persistence owners.
- `report.py` depends on `benchmark.py` for benchmark semantics and on `visualization.py` for figure generation.
- `cli.py` depends on `schemas.py` for runtime request object construction and on `experiment_runner.py` for workflow execution.
- `README.md`, `PROJECT_BRIEF.md`, and docstrings depend on these authoritative owners and must be treated as derived documentation.

## Failure modes if this boundary is violated

- If `config.py` and `data_loader.py` both define authoritative market-data schema rules, CSV acceptance will drift and the same file may pass one path and fail another.
- If `schemas.py` and `storage.py` both own persisted artifact schema, serialized JSON/CSV layout will drift from in-memory result structure and break report or CLI assumptions.
- If `backtest.py` and `metrics.py` both interpret turnover or trade boundaries, reported analytics will no longer match executed trades.
- If `report.py` recomputes benchmark or metric semantics instead of consuming authoritative owners, HTML output can disagree with saved summaries and CLI payloads.
- If `search.py` and the strategy implementation modules both own parameter-validity semantics without authoritative priority, invalid combinations may be filtered differently in CLI, search, and direct strategy execution.
- If `experiment_runner.py` retains workflow-specific schema assembly that duplicates `storage.py`, new workflows will force changes in multiple files and create god-module growth.
- If `cli.py` hardcodes output path conventions independently of `storage.py`, command payloads will advertise artifacts that are never actually written.
- If repo tooling is imported into runtime code, local-machine developer workflow dependencies will contaminate product execution and make reproducibility environment-dependent.

## Migration notes from current implementation

### D. Known overlap risks in current implementation

- `config.py` currently holds `REQUIRED_COLUMNS`, `CSV_COLUMN_ALIASES`, and `MISSING_DATA_POLICY` constants while `data_loader.py` executes those rules.
  - Migration direction: keep `data_loader.py` authoritative for canonical market-data schema and validation behavior; treat `config.py` constants as implementation inputs only if still needed.
- `schemas.py` no longer owns backtest runtime column lists; runtime artifact column ownership now lives with `backtest.py`, while persistence and presentation column ownership live with their respective modules.
- `twse_client.py` currently normalizes directly into the same OHLCV column names enforced by `data_loader.py`.
  - Migration direction: keep `twse_client.py` authoritative only for adapter normalization; `data_loader.py` remains authoritative when remote normalization and local validation disagree.
- The runner layer now splits ownership between:
  - `experiment_runner.py` for public façade and compatibility bundles,
  - `runner_workflows.py` for search, validation, walk-forward, and report workflow orchestration,
  - `runner_protocols.py` for shared runner-only helper logic.
  - Migration direction: keep orchestration split across these modules and do not collapse them back into one file as second-family work begins.
- `report.py` currently calls `benchmark.py` directly and saves reports.
  - Migration direction: keep report rendering and report-file persistence in `report.py`; do not move benchmark semantics or output directory naming into the report layer.
- `storage.py` currently derives ranked-results columns from runtime result objects and also serializes workflow summaries.
  - Migration direction: keep `storage.py` authoritative for persisted artifact schema and naming; require CLI and README to derive from storage-owned schemas rather than restating them independently.
- `README.md`, `PROJECT_BRIEF.md`, and docstrings currently describe architecture and output layout.
  - Migration direction: treat them as derived documentation that must be synchronized to authoritative specs and code owners.
- `obsidian_logger.py` and `scripts/read_memory.py` currently live in the repo tree and can appear architecturally adjacent to runtime modules.
  - Migration direction: keep them explicitly out of product runtime classification and document that they are repo-tooling-only.

### E. Migration priorities

1. Freeze authoritative ownership for market-data schema, in-memory result schemas, persisted artifact schemas, and artifact directory layout.
2. Split `experiment_runner.py` responsibilities conceptually into named orchestration jobs without introducing new files unless a specific ownership conflict cannot otherwise be resolved.
3. Remove persistence-only and presentation-only schema ownership from places that currently duplicate them outside `storage.py` and `report.py`.
4. Label duplicated validation explicitly as authoritative or advisory, starting with strategy parameter validation and market-data validation.
5. Update README, PROJECT_BRIEF, and docstrings so they describe derived behavior from authoritative owners instead of acting as parallel sources of truth.

## Open questions / deferred decisions

- Whether report HTML file persistence should remain in `report.py` or move into `storage.py` as long as `report.py` remains the authoritative rendering owner.
- Whether any future cross-family report-only column contract should live in `visualization.py` or a narrower presentation helper if it stops being runtime-shared.
- Whether `runner_protocols.build_strategy()` should remain a temporary orchestration helper or move into a dedicated strategy registry only when more than one strategy family exists.
- Whether `save_experiment_report()` should be classified as report rendering support or persistence support once multiple report formats exist.

## Boundary violations that would create long-term maintenance debt

- `cli.py` adding its own ranked-results filename logic instead of deriving from `storage.py`.
  - Concrete debt: CLI output can point to `ranked_results.csv` while storage starts writing a different filename or folder structure.
- `report.py` recalculating Sharpe ratio or drawdown instead of consuming `metrics.py`.
  - Concrete debt: HTML report numbers diverge from `metrics_summary.json`, making debugging impossible from persisted artifacts alone.
- `experiment_runner.py` introducing inline parameter filtering rules beyond calling `search.py` and strategy construction.
  - Concrete debt: search results differ depending on whether they are run through CLI, runner internals, or direct module calls.
- `twse_client.py` owning missing-data policy in addition to payload normalization.
  - Concrete debt: TWSE-ingested data and CSV-loaded data follow different cleanup semantics even though they are supposed to converge into one canonical market-data schema.
- `schemas.py` and `storage.py` both defining ranked-results column order.
  - Concrete debt: new metrics or parameter columns appear in one artifact path but not another, creating silent downstream parsing failures.
- `visualization.py` silently requiring columns that are not part of any authoritative contract.
  - Concrete debt: plotting succeeds only for some workflow paths, and failures surface as presentation bugs instead of contract violations.
- Runtime code importing `obsidian_logger.py` or `scripts/read_memory.py`.
  - Concrete debt: local developer tooling becomes a hidden production dependency and breaks reproducibility across machines.
