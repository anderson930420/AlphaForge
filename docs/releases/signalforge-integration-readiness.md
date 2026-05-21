# SignalForge Integration Readiness

## Verdict

READY FOR FIRST END-TO-END DEMO.

AlphaForge is ready to demonstrate the file-based SignalForge-to-AlphaForge handoff for a single-asset long/flat external signal. The current checkpoint proves AlphaForge can consume SignalForge v0.1-style artifacts through `custom_signal`, validate the signal contract, run the research validation/backtest flow, and produce evidence artifacts without importing SignalForge.

## Scope

This readiness checkpoint covers the AlphaForge side of the integration boundary:

- accepting a canonical SignalForge `signal.csv`
- validating schema, timing, symbol, date alignment, and multi-signal selection rules
- mapping binary signals into AlphaForge target positions
- running AlphaForge research validation and backtest evidence workflows
- documenting the file-based handoff contract and current limitations

It does not certify live trading, portfolio construction, broker execution, or SignalForge factor generation.

## Completed Capabilities

- `custom_signal` accepts externally generated SignalForge-style signal files.
- AlphaForge validates the canonical `signal.csv` schema before execution.
- `signal_binary` controls long/flat `target_position` values.
- `signal_value` is preserved as input data but ignored for execution.
- Missing signal dates default to flat positions.
- Extra signal dates not present in market data fail validation.
- Multiple `signal_name` values require explicit `signal_name` selection.
- The research validation/backtest workflow completes using SignalForge-style fixture artifacts.
- The integration smoke path asserts AlphaForge does not import the SignalForge runtime.
- Repo-wide lint, tests, and OpenSpec validation are green at this checkpoint.

## Accepted Signal Schema

AlphaForge accepts the following SignalForge `signal.csv` columns:

```text
datetime
available_at
symbol
signal_name
signal_value
signal_binary
source
```

## Execution Law

The execution law is intentionally narrow:

- `signal_binary = 1` maps to `target_position = 1.0`
- `signal_binary = 0` maps to `target_position = 0.0`
- `signal_value` is ignored for execution

AlphaForge does not infer sizing from `signal_value` and does not search for better SignalForge signals by backtest performance.

## No-Lookahead Rules

AlphaForge enforces the following no-lookahead and alignment rules:

- `available_at <= datetime`
- market data must represent one symbol for `custom_signal` validation
- signal symbol must match the requested or market-data symbol
- signal dates must align to market-data dates
- missing signal dates default to flat positions
- extra signal dates fail validation
- duplicate `datetime`/`symbol`/`signal_name` rows fail validation

## Multi-Signal Behavior

When a `signal.csv` contains more than one `signal_name`, AlphaForge requires explicit `signal_name` selection. This keeps multi-signal files deterministic and avoids silently selecting a signal.

## Boundary

The integration boundary is file-based:

- AlphaForge does not import SignalForge runtime code.
- AlphaForge does not call SignalForge APIs.
- AlphaForge does not compute SignalForge factors.
- SignalForge does not run AlphaForge backtests.
- AlphaForge owns validation, backtesting, metrics, evidence, and persistence.
- SignalForge owns signal generation and the `signal.csv` handoff artifact.

## Validation Evidence

Current validation evidence for this readiness checkpoint:

- `python3 -m pytest`: 262 passed
- `openspec validate --all --strict`: 27 passed
- `ruff check .`: passed
- custom signal focused tests: 17 passed

The focused custom signal validation command was:

```bash
python3 -m pytest tests/test_custom_signal.py tests/test_signalforge_integration.py
```

## Known Limitations

- Long/flat only.
- No portfolio blending.
- No live trading.
- No broker execution.
- File-based handoff only.
- `signal_value` is ignored for sizing.
- No SignalForge runtime integration.
- No AlphaForge-side factor calculation.
- No performance-based signal search for SignalForge outputs.

## Suggested Next Milestones

1. Run the first real SignalForge-produced `signal.csv` through AlphaForge against matching market data.
2. Add a sample command transcript from the first real end-to-end demo.
3. Decide whether to version a formal external artifact contract beyond the current docs and fixture bundle.
4. Add a release checklist for future SignalForge artifact versions.
5. Add portfolio and sizing design notes only after the long/flat file handoff is stable.
