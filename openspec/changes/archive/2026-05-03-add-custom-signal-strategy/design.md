# Design: add-custom-signal-strategy

## Canonical ownership mapping

- `src/alphaforge/custom_signal.py` owns external `signal.csv` validation and `target_position = float(signal_binary)` derivation.
- `src/alphaforge/strategy_registry.py` owns family registration metadata for `custom_signal`, but not signal parsing or signal-value generation.
- `src/alphaforge/search.py` owns search-space generation only for search-capable strategy families and must reject `custom_signal`.
- `src/alphaforge/cli.py` owns request assembly for `research-validate --strategy custom_signal --signal-file ...`, but not file-content validation.
- `src/alphaforge/runner_workflows.py` and `src/alphaforge/runner_protocols.py` own orchestration of validated target positions into the existing research-validation flow.
- `src/alphaforge/backtest.py` remains the execution owner and continues to apply the legacy close-to-close lagged execution semantics.
- `src/alphaforge/storage.py` and `src/alphaforge/report.py` remain derived consumers only.

## Contract migration plan

- Introduce the custom-signal boundary as the canonical place where external signal files are read, validated, and converted into target positions.
- Expose `custom_signal` as a registered workflow family so research-validation can select it, but keep the registry from parsing files or computing `signal_value`.
- Route `research-validate` requests carrying `--signal-file` through the custom-signal boundary before any execution or evidence generation.
- Keep the existing execution law unchanged so validated target positions still run through `backtest.py` with one-bar lagged position realization.
- Keep `search.py` focused on parameter-grid search families and reject `custom_signal` as a validation-only workflow.

## Duplicate logic removal plan

- Remove any signal-file parsing, signal-date validation, or binary-to-target derivation that appears outside `custom_signal.py`.
- Remove any attempt to compute `signal_value` inside AlphaForge runtime code.
- Keep `cli.py`, `runner_workflows.py`, `storage.py`, and `report.py` from duplicating signal validation or ownership of the external file contract.
- Keep `search.py` from becoming a second owner of custom-signal validation by rejecting it rather than enumerating it.

## Verification plan

- Add tests that prove `custom_signal.py` accepts valid signal files and rejects invalid rows for missing datetime, missing available_at, missing symbol, non-binary `signal_binary`, duplicate datetime per symbol, date misalignment, and missing dates.
- Add tests that prove `signal_value` is ignored for execution and that the code path does not import SignalForge internals.
- Add tests that prove `research-validate` can accept a signal-file path for `custom_signal`.
- Add tests that prove `search.py` rejects `custom_signal` as a search-space family.
- Add tests that prove the validated signal-derived targets still run through the existing legacy close-to-close lagged execution semantics.

## Temporary migration states

- None planned.
- The implementation should move the custom-signal contract directly into the new owner instead of keeping duplicate validation in CLI, runner, or strategy code.
