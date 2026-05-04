# report-view-model-contract Specification

## Purpose
TBD - created by archiving change formalize-report-view-model-contract. Update Purpose after archive.
## Requirements
### Requirement: `report.py` is the canonical owner of report view-model assembly

`src/alphaforge/report.py` SHALL be the single authoritative owner of report view-model assembly and report-render input semantics for AlphaForge presentation surfaces.

#### Purpose

- Freeze one report-input contract family so single-run, search comparison, validation, and walk-forward reporting all consume the same explicit semantics.
- Prevent `experiment_runner.py`, `search_reporting.py`, `visualization.py`, and `storage.py` from becoming parallel owners of report-field meaning or report-link semantics.
- Make the report boundary explicit so rendering can stay presentation-only and never become a hidden analytics or orchestration layer.

#### Canonical owner

- `src/alphaforge/report.py` is the only authoritative owner of:
  - report view-model field meaning,
  - report input shaping rules,
  - report-ready display metadata,
  - report-facing link presentation.
- `src/alphaforge/search_reporting.py` and `src/alphaforge/experiment_runner.py` may gather upstream facts and hand them to report-owned helpers, but they must not define the canonical report contract.
- `src/alphaforge/visualization.py` is downstream of assembled figure inputs only.
- `src/alphaforge/storage.py` remains the authoritative owner of artifact paths, filenames, and output layout.
- `src/alphaforge/schemas.py`, `src/alphaforge/backtest.py`, `src/alphaforge/metrics.py`, and `src/alphaforge/benchmark.py` remain the authoritative owners of upstream domain facts that report inputs may consume.

#### Allowed responsibilities

- `report.py` MAY:
  - define report input dataclasses and helpers for each report mode,
  - separate domain facts from presentation refs,
  - validate that required upstream facts are present before rendering,
  - render HTML or other human-readable report content from already-assembled inputs,
  - choose report section ordering, table grouping, display labels, and titles,
  - render relative links from explicit storage refs and explicit link bases,
  - pass chart-ready slices to `visualization.py` for figure construction.

#### Explicit non-responsibilities

- `report.py` MUST NOT:
  - compute execution semantics,
  - compute benchmark semantics,
  - compute metric formulas,
  - infer persisted artifact layout from runtime objects,
  - own output filenames or directory structure for persisted artifacts,
  - own figure-generation semantics or chart-building rules,
  - reconstruct missing upstream facts from storage refs or display labels.
- `search_reporting.py` MUST NOT become the long-term owner of report field meaning just because it loads search artifacts.
- `experiment_runner.py` MUST NOT define report input shapes ad hoc just because it orchestrates workflow steps.
- `visualization.py` MUST NOT own the report-view-model contract.
- `storage.py` MUST NOT redefine report content semantics through file paths or serialized receipts.

#### Inputs / outputs / contracts

- The canonical report-view-model family is a structured composite, not a loose dict.
- Each report-mode input MUST separate:
  - `domain_facts`: already-computed upstream facts,
  - `presentation_refs`: storage-owned or display-only references,
  - `figure_inputs`: chart-ready frames or tables,
  - `table_inputs`: already-shaped rows or summaries.
- Single-run reporting uses `ExperimentReportInput` as the canonical input contract for one experiment report.
- Search comparison reporting uses a search-mode report input that carries ranked results, artifact receipts, top equity curves, and explicit link context.
- Validation reporting uses a validation-mode report input that carries the validation result plus any explicit presentation refs required for the rendered output.
- Walk-forward reporting uses a walk-forward report input that carries the walk-forward result plus fold-level and aggregate presentation data.
- Report renderers MUST consume structured report inputs only; they MUST NOT consume raw orchestration bundles or infer contract fields from ad hoc kwargs.

#### Invariants

- Every report-mode input has already-computed facts available before rendering begins.
- Presentation refs are opaque references, not business truth.
- Report rendering may format and arrange data for display, but it may not silently invent missing business facts.
- If a required fact is absent, report assembly MUST fail fast instead of delegating the omission to rendering.

#### Cross-module dependencies

- `experiment_runner.py` provides orchestration outputs and may call report-owned helpers, but it is downstream of the report contract.
- `search_reporting.py` gathers search-specific artifacts and feeds report-owned inputs into rendering.
- `storage.py` provides canonical artifact refs that may be embedded in the report presentation envelope.
- `visualization.py` renders figures from already-shaped inputs supplied by `report.py`.
- `cli.py` may display rendered report refs or summaries, but it does not define report-input meaning.

#### Failure modes if this boundary is violated

- Report output drifts across workflows because each caller invents its own input shape.
- Report links start acting like hidden storage truth because presentation refs are mixed into facts.
- Search, validation, and walk-forward presentations disagree because the same upstream result is reshaped differently in each caller.
- Figure validation becomes a second analytics layer because chart preconditions are treated as report semantics.

#### Migration notes from current implementation

- `report.py` already defines `ExperimentReportInput` and `SearchReportLinkContext`, which makes it the natural home for the report contract family.
- `experiment_runner._run_experiment_on_market_data()` currently constructs `ExperimentReportInput` inline, so runner code is partially shaping report input today.
- `search_reporting.py` currently constructs `ExperimentReportInput` and `SearchReportLinkContext` while loading stored artifacts, so it acts as a second report-input assembler.
- `visualization.py` currently validates report-facing equity-curve columns internally, but it has no report-level input contract of its own.
- Validation and walk-forward outputs already carry summary path refs in runner and storage code, but there is no explicit report-view-model contract for those presentation surfaces yet.

#### Open questions / deferred decisions

- Whether the report input family should eventually move into a dedicated `report_models.py` module if the contract grows is deferred.
  - Recommended default: keep the canonical owner in `report.py` until a second presentation subsystem proves that split is necessary.
- Whether validation and walk-forward reporting will render HTML pages, CLI summaries, or both is deferred.
  - Recommended default: fix the input contract now and let each presentation surface render from the same shaped inputs later.
- Whether `search_reporting.py` remains a thin adapter or is later folded into `report.py` is deferred.
  - Recommended default: keep it as a search-specific adapter while the contract stabilizes.

#### Scenario: single-run reports render from a canonical view-model

- GIVEN a single experiment has already produced `ExperimentResult`, an equity curve, trades, and benchmark facts
- WHEN report assembly creates the single-run report input
- THEN the report renderer SHALL consume that structured input directly
- AND it SHALL NOT recompute metrics, benchmark values, or execution behavior

#### Scenario: search comparison reports use explicit artifact refs

- GIVEN ranked search results and storage-owned receipts are available
- WHEN the search comparison report input is assembled
- THEN the input SHALL carry explicit artifact refs and explicit link context
- AND the renderer SHALL NOT infer artifact filenames or directory layout from ranked result objects

#### Scenario: visualization remains a downstream figure renderer

- GIVEN a report input includes chart-ready equity curves and trade overlays
- WHEN `visualization.py` builds figures
- THEN it SHALL consume the prepared figure inputs only
- AND it SHALL NOT own the report-view-model contract or recompute missing business facts

### Requirement: report view-models separate domain facts from presentation refs

Report view-models in AlphaForge SHALL distinguish authoritative upstream domain facts from presentation-only refs and display metadata.

#### Purpose

- Prevent report links, artifact paths, and display labels from being mistaken for business truth.
- Prevent report code from recreating persistence semantics or upstream analytics from presentation scaffolding.

#### Canonical owner

- `src/alphaforge/report.py` is the authoritative owner of the fact-vs-presentation split for report inputs.
- `src/alphaforge/storage.py` remains the authoritative owner of canonical artifact path facts.
- `src/alphaforge/schemas.py`, `src/alphaforge/backtest.py`, `src/alphaforge/metrics.py`, `src/alphaforge/benchmark.py`, and `src/alphaforge/experiment_runner.py` remain the authoritative owners of upstream domain facts.

#### Allowed responsibilities

- Domain facts MAY include:
  - `ExperimentResult`
  - `ValidationResult`
  - `WalkForwardResult`
  - `MetricReport`
  - benchmark summaries
  - ranked results and fold summaries
  - figure-ready data frames that already reflect upstream computation
- Presentation refs MAY include:
  - `ArtifactReceipt`
  - `report_path`
  - `best_report_path`
  - `comparison_report_path`
  - `search_report_path`
  - relative links
  - display titles
  - display names
  - label text used only for presentation

#### Explicit non-responsibilities

- Presentation refs MUST NOT be treated as substitutes for authoritative upstream facts.
- Domain facts MUST NOT be replaced by inferred path text, display labels, or relative links.
- Report code MUST NOT derive benchmark or execution truth from artifact paths.
- Storage code MUST NOT attach new business meaning to display-only refs.

#### Inputs / outputs / contracts

- The report view-model MUST carry both the domain facts and the presentation envelope when links or display metadata are needed.
- The presentation envelope MAY omit refs that are not required for the rendered view.
- If a report mode does not need links, it MUST NOT invent them just to complete the shape.

#### Invariants

- A report may render without presentation refs if the rendered surface does not need links.
- A presentation ref may be absent without changing the underlying domain facts.
- A report renderer may format presentation refs for display, but it may not use them as an alternate source for missing business data.

#### Cross-module dependencies

- `storage.py` provides the canonical artifact path refs that can be embedded in presentation envelopes.
- `experiment_runner.py` and `search_reporting.py` may pass through presentation refs, but they do not own their meaning.
- `cli.py` may print presentation refs, but it must not reinterpret them as canonical storage truth.

#### Failure modes if this boundary is violated

- Report links become brittle because display text starts standing in for real paths.
- Report content drifts because missing domain facts are silently rebuilt from presentation refs.
- Search comparison tables disagree with storage because links are guessed instead of derived from canonical refs.
- Validation and walk-forward summaries become hard to audit because presentation metadata is treated as result truth.

#### Migration notes from current implementation

- `ArtifactReceipt` already separates canonical persisted refs from optional presentation refs.
- `SearchReportLinkContext` already distinguishes link-base semantics from display-only naming.
- `experiment_runner.py` currently passes report-relevant values through orchestration bundles, which makes the fact-vs-presentation split easy to blur.
- `report.py` currently renders relative paths and labels directly, so the contract needs to keep those values explicitly classified as presentation metadata.

#### Open questions / deferred decisions

- Whether a dedicated `ReportPresentationEnvelope` dataclass should be introduced later is deferred.
  - Recommended default: keep the split explicit in the report contract first, then introduce a helper dataclass only if the family grows further.

#### Scenario: presentation refs never replace canonical facts

- GIVEN a report input contains both a benchmark summary and a best-report path
- WHEN the renderer builds the output
- THEN it SHALL use the benchmark summary for business numbers
- AND it SHALL use the path only as presentation metadata
- AND it SHALL NOT derive any benchmark value from the path text

### Requirement: report rendering and visualization consume pre-shaped inputs only

Report rendering and figure generation in AlphaForge SHALL consume already-assembled inputs and SHALL NOT become recomputation layers for execution, metrics, benchmark, or persistence semantics.

#### Purpose

- Keep rendering focused on presentation so upstream analytics remain authoritative and debuggable.
- Prevent figure and report code from becoming a second place where business rules are quietly re-evaluated.

#### Canonical owner

- `src/alphaforge/report.py` is authoritative for report composition and report layout decisions.
- `src/alphaforge/visualization.py` is authoritative for figure construction from prepared figure inputs only.
- `src/alphaforge/backtest.py`, `src/alphaforge/metrics.py`, and `src/alphaforge/benchmark.py` remain the authoritative owners of the numeric semantics that reports display.

#### Allowed responsibilities

- `report.py` MAY:
  - format numbers, rows, and sections for display,
  - sort already-prepared display rows for presentation only,
  - choose table grouping and heading order,
  - embed figures produced by `visualization.py`,
  - render explicit links from explicit refs.
- `visualization.py` MAY:
  - validate chart-ready columns needed for figure construction,
  - convert already-computed frames and trade tables into figures,
  - choose chart styling and trace layout.

#### Explicit non-responsibilities

- `report.py` MUST NOT compute metrics, benchmark summaries, or execution semantics.
- `report.py` MUST NOT infer missing report facts by reading storage paths or by rebuilding data from raw market files.
- `visualization.py` MUST NOT compute the report-view-model contract, benchmark semantics, or execution semantics.
- `visualization.py` MUST NOT reconstruct missing report inputs from raw upstream objects.

#### Inputs / outputs / contracts

- Report rendering inputs:
  - mode-specific report view-models from `report.py`
  - explicit storage refs when links are rendered
  - already-computed figure inputs for charts
- Figure rendering inputs:
  - equity-curve frames
  - benchmark comparison frames
  - trade-log frames
  - ranked equity-curve overlays
- Output:
  - rendered report content or saved report artifacts
  - figures embedded in or attached to rendered output

#### Invariants

- Any metric, benchmark, or execution number shown in a report must already exist upstream before rendering begins.
- Figure validation is presentation-only and does not change the authoritative meaning of the data.
- Rendering may fail fast on missing inputs, but it may not fill them in with guessed semantics.

#### Cross-module dependencies

- `experiment_runner.py` and `search_reporting.py` supply already-computed inputs.
- `storage.py` supplies canonical artifact refs that may be displayed as links.
- `visualization.py` receives figure-ready slices from `report.py` and never becomes the owner of report semantics.

#### Failure modes if this boundary is violated

- HTML reports and figures can disagree with persisted summaries if rendering recomputes numbers locally.
- Chart failures become hidden data-contract failures if visualization starts owning report field semantics.
- Report outputs stop matching CLI and storage artifacts if presentation code starts inventing missing values.

#### Migration notes from current implementation

- `report.py` already formats metrics and invokes figure builders, which is correct only if those inputs are fully computed before rendering.
- `visualization.py` already validates chart-required columns such as equity-curve fields, but that validation must remain presentation-only.
- `search_reporting.py` currently loads persisted CSVs before report rendering, which is acceptable as an input-gathering step but not as an analytics owner.

#### Open questions / deferred decisions

- Whether chart-ready input helpers should live only in `report.py` or be split into a small shared figure-input module later is deferred.
  - Recommended default: keep the input contract report-owned and let visualization remain a pure renderer.

#### Scenario: rendering does not recompute business rules

- GIVEN a report input already contains metrics and benchmark summaries
- WHEN the report renderer formats the output
- THEN it SHALL use those values as authoritative
- AND it SHALL NOT recompute them from raw frames or storage refs

### Requirement: mode-specific report contracts are explicit for single-run, search, validation, and walk-forward surfaces

Each report mode in AlphaForge SHALL have an explicit report input contract so the required upstream facts and allowed presentation refs are unambiguous.

#### Purpose

- Prevent the single-run, search, validation, and walk-forward surfaces from drifting into different ad hoc input shapes.
- Make it obvious which fields are mandatory and which are presentation-only for each mode.

#### Canonical owner

- `src/alphaforge/report.py` is authoritative for the shape of each mode-specific report input.
- `src/alphaforge/experiment_runner.py` and `src/alphaforge/search_reporting.py` may populate those inputs from upstream results, but they do not own the mode contracts.

#### Allowed responsibilities

- Single-run report inputs MAY require:
  - `result: ExperimentResult`
  - `equity_curve: EquityCurveFrame`
  - `trades: pd.DataFrame`
  - `benchmark_summary: dict[str, float]`
  - `benchmark_curve: EquityCurveFrame`
- Search comparison report inputs MAY require:
  - `ranked_results: list[ExperimentResult]`
  - `artifact_receipts: list[ArtifactReceipt | None]`
  - `top_equity_curves: dict[str, EquityCurveFrame]`
  - `link_context: SearchReportLinkContext`
  - optional `best_report_path: Path | None`
  - optional `comparison_report_path: Path | None`
- Validation report inputs MAY require:
  - `validation_result: ValidationResult`
  - `train_ranked_results_path: Path | None`
  - explicit presentation refs for train and test artifacts when a report or summary needs links
- Walk-forward report inputs MAY require:
  - `walk_forward_result: WalkForwardResult`
  - fold-level presentation refs when a report or summary needs links
  - aggregate metrics already computed upstream

#### Explicit non-responsibilities

- A report mode MUST NOT accept partially shaped runtime objects and then invent missing contract fields internally.
- A report mode MUST NOT rely on hidden runner state to fill in links, labels, or fold paths.
- A report mode MUST NOT infer field requirements from the CLI command that happened to trigger it.

#### Inputs / outputs / contracts

- Shared family:
  - report modes share the same design rule: upstream facts first, presentation refs second.
- Single-run:
  - the renderer gets one experiment's domain facts and figure inputs.
- Search comparison:
  - the renderer gets ranked results plus explicit storage refs for run-level artifacts.
- Validation:
  - the renderer gets the validation result plus any report-facing refs for train and test outputs.
- Walk-forward:
  - the renderer gets the walk-forward result plus fold-level and aggregate presentation refs.

#### Invariants

- The required fields for each mode are fixed by the report contract, not by the caller that assembled them.
- Each mode may add optional presentation refs, but it may not silently drop required domain facts.
- A future report renderer can be added for a mode without redefining the mode's field meaning.

#### Cross-module dependencies

- `experiment_runner.py` must hand validation and walk-forward outputs to report-owned helpers if it wants report-style presentation.
- `search_reporting.py` must hand search-specific artifacts to report-owned helpers rather than defining its own semantic shape.
- `storage.py` may provide refs used in these inputs, but it does not define the report contract.

#### Failure modes if this boundary is violated

- Search, validation, and walk-forward presentations diverge because each mode accepts a different ad hoc payload shape.
- Report code starts depending on orchestration internals that are not stable API.
- Missing presentation refs cause hidden fallbacks that make links and labels inconsistent across modes.

#### Migration notes from current implementation

- Single-run reporting already has an explicit `ExperimentReportInput` in `report.py`.
- Search comparison reporting already uses `SearchReportLinkContext`, ranked results, explicit artifact receipts, and top equity curves.
- Validation and walk-forward workflows already produce structured runtime results, but they do not yet have a report-view-model family that is equally explicit.
- This change should make those surfaces symmetrical even if their renderers are added incrementally.

#### Open questions / deferred decisions

- Whether validation and walk-forward report renderers will ultimately live in `report.py` or a sibling presentation module is deferred.
  - Recommended default: keep the input contract in `report.py` and let the renderer placement follow the existing presentation boundary.

#### Scenario: each mode rejects missing contract fields instead of guessing

- GIVEN a search comparison report input is missing the ranked results list
- WHEN report assembly validates the input
- THEN it SHALL fail fast
- AND it SHALL NOT infer the missing list from runner state or persisted filenames

### Requirement: report wording preserves return-based trade semantics

`src/alphaforge/report.py` SHALL render trade-related labels using return-based terminology and SHALL NOT relabel the canonical trade contract as dollar PnL.

#### Purpose

- Keep display wording aligned with the return-based artifact and metric contracts.
- Prevent report text from undoing the semantics hardening performed in backtest, metrics, and storage.

#### Canonical owner

- `src/alphaforge/report.py` is the authoritative owner of display wording only.
- `src/alphaforge/storage.py` remains the authoritative owner of the artifact schema being displayed.
- `src/alphaforge/backtest.py` remains the authoritative owner of trade semantics.

#### Allowed responsibilities

- `report.py` MAY display `trade_gross_return`, `trade_net_return`, `cost_return_contribution`, and `holding_period` using human-friendly labels.
- `report.py` MAY display the execution-semantics metadata string `legacy_close_to_close_lagged`.
- `report.py` MAY format percentages and bar counts for presentation.

#### Explicit non-responsibilities

- `report.py` MUST NOT rename return-based trade fields into dollar-PnL language.
- `report.py` MUST NOT imply shares-level accounting, partial fills, or broker-like execution.
- `report.py` MUST NOT recompute trade returns or win rate from raw market data.
- `report.py` MUST NOT infer alternate semantics from artifact names alone.

#### Inputs / outputs / contracts

- Inputs:
  - the return-based trade log from storage or runtime result objects
  - execution-semantics metadata from the backtest contract
  - computed metrics from `metrics.py`
- Outputs:
  - human-readable report labels and sections
- Contract rules:
  - user-facing labels may be friendlier than field names, but they must preserve the return-based meaning
  - report wording must stay consistent with the storage-owned `trade_log.csv` schema

#### Invariants

- Report wording stays downstream of the canonical field names.
- Return-based trade fields are not translated into dollar accounting terms.
- Report rendering does not become a second semantics owner.

#### Cross-module dependencies

- `storage.py` supplies the canonical persisted fields.
- `backtest.py` supplies the canonical semantics.
- `metrics.py` supplies computed metric values such as win rate.
- `cli.py` may print report paths or summaries, but it must not invent alternate wording.

#### Failure modes if this boundary is violated

- The report can say "PnL" while the storage schema and runtime contract say "return", which makes the artifact set internally inconsistent.
- Users can misread the report as showing dollar accounting.
- Legacy wording can survive even after the persisted schema is hardened.

#### Migration notes from current implementation

- The current report layer already renders presentation text from upstream inputs.
- This change requires those labels to move with the new return-based trade schema in the same controlled migration.

#### Open questions / deferred decisions

- None for display wording.

#### Scenario: reports render return-based trade labels

- GIVEN a report renders trade details from the persisted trade log
- WHEN it displays the trade fields
- THEN it SHALL preserve return-based terminology
- AND it SHALL NOT relabel the canonical trade contract as dollar PnL

### Requirement: reports display minimal evidence diagnostics when present

`src/alphaforge/report.py` SHALL render cost-sensitivity diagnostics and bootstrap evidence diagnostics when those diagnostics are present in the report input metadata or result payload.

#### Scenario: report exposes diagnostic summaries

- GIVEN a research-validation report input contains cost sensitivity and bootstrap evidence
- WHEN the report is rendered
- THEN the HTML SHALL include a cost-sensitivity section
- AND it SHALL include a bootstrap-evidence section
- AND it SHALL present the diagnostics as evidence, not as full execution realism

### Requirement: report wording remains diagnostic-only

The rendered report SHALL describe the diagnostics as minimal research evidence and SHALL NOT claim a full TCA simulator, broker execution simulation, or advanced multiple-testing correction framework.

#### Scenario: report does not overclaim

- GIVEN diagnostic sections are displayed
- WHEN the report is read by a user
- THEN the wording SHALL remain limited to cost sensitivity and bootstrap evidence
- AND it SHALL NOT imply PBO, DSR, White Reality Check, Hansen SPA, or other advanced corrections

