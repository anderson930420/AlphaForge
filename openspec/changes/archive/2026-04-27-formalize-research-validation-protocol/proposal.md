# Proposal: formalize-research-validation-protocol

## Boundary problem

- AlphaForge has strategy search, validation search, walk-forward validation, permutation diagnostics, research-policy guardrails, and comparison workflows, but no canonical research-process protocol that defines how these workflows are sequenced for multi-year strategy research.
- Final holdout protection is currently implicit in workflow usage rather than owned by a formal protocol boundary.
- Without a protocol boundary, strategy search, scoring-rule selection, risk-filter selection, walk-forward validation, permutation diagnostics, and final reporting can drift into ad hoc workflows that accidentally tune against final holdout data.
- Permutation diagnostics already have a dedicated null-comparison contract, but the higher-level research process needs to define that permutation evidence is robustness evidence, not standalone proof of profitability.

## Canonical ownership decision

- The OpenSpec capability `research-validation-protocol` becomes the canonical owner of the multi-year research protocol contract.
- Runtime modules such as `backtest.py`, market data loaders, strategy implementations, storage, CLI formatting, and report rendering must not own or redefine this protocol.
- Existing search, validate-search, walk-forward validation, permutation, policy, and reporting concepts remain responsible for their own execution details and artifacts; this protocol coordinates their allowed use across development and final holdout periods.
- Strategy families must not own final holdout protection. Holdout protection is a research-process boundary.

## Scope

- Define development and final holdout separation for multi-year OHLCV research.
- Require the final holdout period to be frozen before development research begins.
- Restrict strategy search, parameter search, scoring-rule selection, risk-filter selection, walk-forward validation, and permutation diagnostics to development data until the final holdout gate is opened.
- Require walk-forward validation to produce multiple out-of-sample folds inside the development period.
- Position permutation diagnostics as robustness diagnostics and prefer block permutation or block shuffle over naive independent row shuffling.
- Define the pre-holdout freeze set: strategy family, parameter selection rule, scoring formula, transaction cost assumptions, risk filters, report format, and acceptance criteria.
- Define the one-time final holdout evaluation rule and prohibit using final holdout results for further tuning.
- Define required final report disclosures at the research-process level.

## Migration risk

- CLI behavior risk is low for this specification-first change because no CLI commands or argument formatting are required to change.
- Persisted artifact risk is low because this change does not own artifact paths, filenames, JSON schemas, or CSV layouts.
- Report behavior risk is limited to future report contract work; this change names disclosure requirements without implementing report rendering.
- Runtime behavior risk is low because this change does not modify backtest execution semantics, market data schema, strategy signal generation, storage layout, or strategy logic.
- Future workflow risk is concentrated in enforcing the protocol without duplicating responsibility in strategy families, storage, report rendering, or backtest modules.

## Acceptance conditions

- `openspec/changes/formalize-research-validation-protocol/proposal.md`, `design.md`, `tasks.md`, and a `research-validation-protocol` spec delta exist.
- The spec delta defines clear MUST / SHOULD requirements for development/holdout separation, development-only walk-forward OOS, permutation diagnostic positioning, one-time final holdout evaluation, and final report disclosures.
- The spec explicitly excludes ownership of backtest execution semantics, market data schema, strategy signal generation, artifact persistence layout, CLI formatting, and report rendering implementation details.
- No runtime strategy logic is introduced.
- `backtest.py` is not modified.
- `openspec validate formalize-research-validation-protocol --type change --no-interactive` passes.
