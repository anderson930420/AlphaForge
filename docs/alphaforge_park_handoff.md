# AlphaForge Park Handoff

AlphaForge is parked as a spec-driven quant research validation engine.

It remains the validation and evidence layer for OHLCV research inputs, built-in strategy backtests, walk-forward validation, permutation diagnostics, and external `signal.csv` validation through `custom_signal`.

## AlphaForge owns

- OHLCV validation and normalization
- single-asset backtests
- metrics, benchmark comparison, and reporting
- built-in strategy search for supported families
- development / final holdout research-validation protocol
- artifact persistence for research runs
- validation of externally generated `signal.csv` files through `custom_signal`

## SignalForge owns next

SignalForge should generate `signal.csv` files and own signal-generation logic.

AlphaForge validates those files, converts `signal_binary` into execution target positions, and runs the research-validation workflow.

## Hermes / research pipeline may orchestrate later

Hermes or a later research pipeline layer may coordinate:

- SignalForge signal generation
- AlphaForge validation and backtesting
- artifact collection and reporting
- experiment scheduling and cross-run orchestration

## Boundary statement

- SignalForge generates `signal.csv`.
- AlphaForge validates `signal.csv` and runs research-validation.
- AlphaForge must not import SignalForge internals.

## Explicit non-goals

AlphaForge is not responsible for:

- live trading
- broker execution
- portfolio optimization
- full TCA simulation
- paper extraction
- factor engineering
- feature mining
- ML model training or selection
- point-in-time fundamentals
- a multi-source institutional data platform
