# Phase 3 Signed Backtest Runtime

## Summary

This phase adds an explicit signed close-to-close runtime while preserving the legacy long-only runtime as the default.

## Execution semantics

AlphaForge now recognizes two execution semantics:

```text
legacy_close_to_close_lagged
signed_close_to_close_lagged
```

The legacy runtime remains the default. It preserves the original long/flat behavior and clips target positions into `[0.0, 1.0]`.

The signed runtime must be requested explicitly. It validates target positions inside `[-1.0, 1.0]` and supports long, flat, and short positions without leverage.

## Runtime rules

Both runtimes use the same timing and return law:

```text
position[t] = target_position[t-1]
strategy_return[t] = position[t] * close_return[t] - turnover_cost[t]
```

For signed runtime:

- positive position means long exposure
- zero position means flat exposure
- negative position means short exposure
- a price decline while short produces positive strategy return
- a direct long to short reversal produces turnover of `2.0`
- leverage outside `[-1.0, 1.0]` fails validation

## Custom signal impact

v0.2 `custom_signal` files can now carry negative `target_weight` values as long as they remain inside `[-1.0, 1.0]`.

This phase only adds the runtime foundation. Existing CLI paths still call the default legacy runtime unless a later phase wires signed semantics through configuration.