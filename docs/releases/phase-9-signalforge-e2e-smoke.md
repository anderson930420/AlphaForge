# Phase 9 SignalForge Cross-Repo CLI E2E Smoke

## Summary

This phase adds a cross-repo smoke script that validates the terminal workflow between SignalForge and AlphaForge.

The script proves this boundary:

```text
SignalForge CLI
  export-alphaforge-v02-smoke
        ↓
SignalForge v0.2 package
        ↓
AlphaForge CLI
  smoke-signalforge-package
        ↓
custom_signal v0.2 + signed_close_to_close_lagged
```

## Command

From the AlphaForge repo:

```bash
python3 scripts/run_signalforge_e2e_smoke.py \
  --signalforge-repo ../SignalForge \
  --package-dir /tmp/signalforge_v02_demo
```

## What It Executes

SignalForge side:

```bash
python3 -m signalforge.cli export-alphaforge-v02-smoke \
  --output-dir /tmp/signalforge_v02_demo \
  --overwrite
```

AlphaForge side:

```bash
python3 -m alphaforge.cli smoke-signalforge-package \
  --package /tmp/signalforge_v02_demo
```

## Acceptance Criteria

The AlphaForge summary must include:

```text
status = passed
signal_contract_version = v0.2
target_position_source_column = target_weight
execution_semantics = signed_close_to_close_lagged
```

The script also checks positive row counts and numeric final equity.

## Boundary

The script does not import SignalForge internals. It only calls SignalForge through its CLI and consumes the exported package through AlphaForge's CLI.
