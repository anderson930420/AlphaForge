# Design: formalize-research-validation-protocol

## Canonical ownership mapping

- `research-validation-protocol` owns the research-process contract for multi-year strategy validation.
- Search and validation workflows own candidate generation, parameter evaluation, and train/test evidence within their existing boundaries.
- Walk-forward validation owns fold construction and fold-level out-of-sample evidence within the development period.
- Permutation diagnostics own null construction and diagnostic summaries, while this protocol owns when permutation diagnostics may be used and how they are interpreted in the research process.
- Research policy guardrails own candidate promotion decisions on already-computed evidence, while this protocol owns the freeze gate before final holdout evaluation.
- Report contracts own rendered representation and output fields; this protocol owns the disclosure obligations that final reports must satisfy.

## Protocol phases

1. Collect multi-year OHLCV data through existing market data contracts.
2. Split the data into a development period and a final holdout period.
3. Freeze the final holdout period before development research begins.
4. Run all strategy family exploration, parameter search, scoring-rule selection, risk-filter selection, walk-forward validation, and permutation diagnostics only on development data.
5. Require walk-forward validation to produce multiple development-period out-of-sample folds.
6. Treat permutation results as robustness diagnostics, preferring block permutation or block shuffle because financial time series may contain local autocorrelation, volatility clustering, and regime structure.
7. Before final holdout access, freeze the strategy family, parameter selection rule, scoring formula, transaction cost assumptions, risk filters, report format, and acceptance criteria.
8. Evaluate the final holdout once.
9. Prohibit final holdout results from tuning parameters, scoring rules, filters, report format, or acceptance criteria.
10. Produce final report disclosures required by the protocol.

## Boundary exclusions

- Do not redefine how backtests execute trades, fees, slippage, positions, fills, or metrics.
- Do not redefine canonical OHLCV schema or market data adapter ownership.
- Do not redefine strategy signal generation or supported strategy-family registry semantics.
- Do not define storage paths, filenames, persistence layout, or serialized artifact schemas.
- Do not define CLI formatting or terminal output behavior.
- Do not implement report rendering in this change.

## Acceptance criteria mapping

- Development/holdout separation: enforced by protocol requirements that split multi-year data and freeze the holdout before research.
- Walk-forward OOS inside development only: enforced by requirements that walk-forward folds are produced entirely inside development data.
- Block permutation positioning: enforced by requirements that permutation is diagnostic-only and should prefer block permutation or block shuffle over independent row shuffling.
- Final holdout one-time evaluation: enforced by requirements that the holdout is evaluated once after the pre-holdout freeze gate.
- Final report disclosure requirements: enforced by requirements naming search-space size, tried families, tried combinations, walk-forward summary, degradation, permutation result, transaction costs, final holdout result, and rejected/failed candidate summary when available.

## Verification plan

- Run `openspec validate formalize-research-validation-protocol --type change --no-interactive`.
- Confirm no runtime source files are changed as part of this specification-first change.
- Confirm `src/alphaforge/backtest.py` is untouched.

## Deferred implementation

- Runtime enforcement of the protocol gate is deferred to a later implementation change.
- Report rendering changes that surface required disclosures are deferred to a later report-contract or workflow-artifact change.
- Storage schema additions for protocol receipts, if needed, are deferred to a storage/artifact contract change.
