# Phase 2 v0.2 Signal Adapter

## Summary

This phase adds consumer-side support for a v0.2 `signal.csv` contract while preserving the existing v0.1 `signal_binary` contract.

## v0.1 behavior

Files without `target_weight` continue to use v0.1 behavior:

- `signal_binary = 1` maps to `target_position = 1.0`.
- `signal_binary = 0` maps to `target_position = 0.0`.
- `signal_value` is ignored for execution.

## v0.2 behavior

Files with `target_weight` are treated as v0.2 and must contain:

```text
datetime
available_at
symbol
signal_name
score
direction
target_weight
source
```

The loader maps `target_weight` to `target_position` for the existing runtime.

Current runtime limits remain explicit:

- `direction` must be `-1`, `0`, or `1`.
- `target_weight` must be between `0.0` and `1.0`.
- Values outside the current runtime range fail validation instead of being silently clipped.

## Boundary

This phase does not change the backtest engine. It only lets AlphaForge read v0.2 target-weight signal files under the current long-only runtime constraints.
