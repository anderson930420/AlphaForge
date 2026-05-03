# Proposal: add-custom-signal-strategy

## Boundary problem

- AlphaForge has no canonical owner for validating externally supplied `signal.csv` files before research evaluation.
- Today, strategy modules own signal generation for built-in strategies, but there is no spec that lets AlphaForge consume a precomputed signal file without treating the file as an internal strategy implementation.
- The `research-validate` workflow needs a supported `custom_signal` path that validates external signal input, maps it to target positions, and still uses AlphaForge's existing execution semantics.

## Canonical ownership decision

- `src/alphaforge/custom_signal.py` becomes the canonical owner of external signal-file validation and target-position derivation for the `custom_signal` workflow.
- `src/alphaforge/backtest.py` remains the canonical owner of execution semantics.
- `src/alphaforge/strategy_registry.py` may register `custom_signal` for workflow dispatch, but it must not compute `signal_value` or parse external signal files.
- `src/alphaforge/runner_workflows.py` may orchestrate passing validated signal-derived target positions into execution, but it must not own signal validation rules.
- `src/alphaforge/cli.py` may accept `--signal-file` for `research-validate`, but it must not validate signal content.

## Scope

- Add a custom-signal interface boundary for validating `signal.csv` input.
- Allow `research-validate --strategy custom_signal --signal-file ...` to accept externally supplied signals.
- Keep AlphaForge from computing signals internally for this workflow.
- Keep the execution law identical to the current legacy close-to-close lagged model.
- Update the relevant boundary specs so search, registry, orchestration, and CLI ownership remain single-sourced.

## Migration risk

- CLI risk is limited to adding a new request shape for `research-validate` and reporting validation failures for malformed signal files.
- Runtime risk is limited to signal-date alignment, duplicate detection, and mapping `signal_binary` to target position.
- Search risk is that `custom_signal` could be treated like a parameter-grid search family unless the search boundary explicitly excludes it.
- Compatibility risk is that external signal files must not be mistaken for an internal strategy implementation or for SignalForge source code.

## Acceptance conditions

- OpenSpec proposal, design, tasks, and spec deltas validate before implementation starts.
- The spec clearly states that AlphaForge validates external `signal.csv` files but does not generate signals.
- The spec clearly states that `custom_signal` uses the current `legacy_close_to_close_lagged` execution semantics.
- The spec clearly states that AlphaForge does not import SignalForge internals.
- `openspec validate add-custom-signal-strategy --type change --no-interactive` passes.
