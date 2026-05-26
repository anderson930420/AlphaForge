# Phase 5 Open Asset Pricing Adapter

## Summary

This phase adds a lightweight offline adapter for Open Asset Pricing-style firm characteristics.

The adapter does not download data. It converts an already loaded characteristic DataFrame into AlphaForge's v0.2 signal file shape:

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

## Design

The first implementation is intentionally small:

```text
characteristic value
        ↓
cross-sectional quantile policy
        ↓
direction
        ↓
target_weight
        ↓
v0.2 signal.csv
```

High signed characteristic scores become long candidates. Low signed characteristic scores become short candidates. Middle observations remain flat.

## Boundary

This phase does not add a live Open Asset Pricing downloader and does not add a multi-asset portfolio backtest engine.

The adapter can generate multi-symbol v0.2 signal frames, but the current custom_signal runtime remains primarily a single-symbol workflow. Full cross-sectional portfolio backtesting should be handled in a later phase.
