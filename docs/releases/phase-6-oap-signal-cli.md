# Phase 6 OAP Signal CLI

## Summary

This phase adds a CLI workflow for converting an Open Asset Pricing-style characteristic CSV into AlphaForge's v0.2 `signal.csv` format.

## Command

```bash
python3 -m alphaforge.cli build-oap-signal \
  --input oap_characteristics.csv \
  --output signal.csv \
  --characteristic BM \
  --date-col date \
  --asset-id-col permno
```

## Output

The generated file uses the v0.2 signal contract:

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

## Boundary

This command reads local CSV files only. It does not download live Open Asset Pricing data and does not add a multi-asset portfolio backtest engine.
