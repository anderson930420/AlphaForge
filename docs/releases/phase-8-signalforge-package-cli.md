# Phase 8 SignalForge Package CLI Workflow

## Summary

This phase adds a CLI command for validating and smoke-testing a SignalForge v0.2 package through AlphaForge.

## Command

```bash
python3 -m alphaforge.cli smoke-signalforge-package \
  --package path/to/signalforge_package
```

## Behavior

The command:

- validates required package files
- validates manifest compatibility
- validates `signal_contract.yaml` compatibility fragments
- loads `signal.csv` through `custom_signal` v0.2
- runs `signed_close_to_close_lagged` backtest smoke
- prints JSON pass summary

## Boundary

This CLI does not import SignalForge internals and does not define a new signal schema.

SignalForge remains the file-artifact producer. AlphaForge remains the file-artifact consumer and runtime validator.
