# SignalForge Integration

AlphaForge consumes SignalForge v0.1 outputs through the `custom_signal` strategy path. The integration boundary is file-based: SignalForge writes artifacts, and AlphaForge reads `signal.csv` as an external signal file.

## Artifact Bundle

A SignalForge v0.1 run is expected to produce:

- `signal.csv`: canonical signal rows consumed by AlphaForge.
- `signal_contract.yaml`: producer-side schema and execution contract metadata.
- `data_quality_report.json`: source OHLCV quality report from SignalForge.

AlphaForge validates and consumes `signal.csv`. The contract and data-quality report are useful handoff evidence, but AlphaForge does not need them at runtime.

The canonical `signal.csv` columns are:

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

AlphaForge uses only `signal_binary` for execution:

- `signal_binary = 1` maps to `target_position = 1.0`
- `signal_binary = 0` maps to `target_position = 0.0`
- `signal_value` is ignored for execution
- missing signal dates default to flat positions
- signal dates that are not present in market data fail validation
- files with multiple `signal_name` values require explicit `--signal-name`

The usual AlphaForge backtest semantics still apply after the target-position series is built.

## Custom Signal Validation Semantics

`custom_signal` is an externally frozen signal workflow. AlphaForge treats the supplied `signal.csv` as a frozen external signal file and does not search, tune, or infer signal parameters from the market data.

For this MVP path, AlphaForge validates the signal schema and alignment rules, then runs the configured development-period evaluation and final-holdout evaluation. It does not perform parameter search, and it does not perform parameter-search walk-forward folds for `custom_signal`.

The runtime may still record a `WalkForwardResult` for evidence consistency, but `walk_forward_summary` may report `fold_count` 0 for `custom_signal` because there are no walk-forward folds in this workflow.

## CLI Examples

Run research validation with a SignalForge signal file:

```bash
python3 -m alphaforge.cli research-validate \
  --strategy custom_signal \
  --data tests/fixtures/signalforge/market_data.csv \
  --symbol SFDEMO \
  --signal-file tests/fixtures/signalforge/signal.csv \
  --development-start 2025-01-02 \
  --development-end 2025-01-08 \
  --holdout-start 2025-01-09 \
  --holdout-end 2025-01-13
```

`--signal-path` is accepted as an alias for `--signal-file`:

```bash
python3 -m alphaforge.cli research-validate \
  --strategy custom_signal \
  --data tests/fixtures/signalforge/market_data.csv \
  --symbol SFDEMO \
  --signal-path tests/fixtures/signalforge/signal.csv \
  --development-start 2025-01-02 \
  --development-end 2025-01-08 \
  --holdout-start 2025-01-09 \
  --holdout-end 2025-01-13
```

For a multi-signal file, select the intended signal explicitly:

```bash
python3 -m alphaforge.cli research-validate \
  --strategy custom_signal \
  --data path/to/market_data.csv \
  --symbol SFDEMO \
  --signal-file path/to/signal.csv \
  --signal-name signalforge_v01_momentum \
  --development-start 2025-01-02 \
  --development-end 2025-01-08 \
  --holdout-start 2025-01-09 \
  --holdout-end 2025-01-13
```

## Boundary

AlphaForge does not import SignalForge, call SignalForge APIs, calculate SignalForge factors, or search for signals by backtest performance. SignalForge does not run AlphaForge backtests.

The handoff contract is intentionally narrow: SignalForge generates a valid `signal.csv`; AlphaForge validates that file, maps `signal_binary` to long/flat target positions, and runs the research validation/backtest workflow.
