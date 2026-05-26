# Phase 4 Wire Execution Semantics into CLI and Config

## Summary

This phase wires AlphaForge execution semantics through the user-facing configuration path.

`BacktestConfig` now carries:

```text
execution_semantics
```

The default remains:

```text
legacy_close_to_close_lagged
```

Users can explicitly request:

```text
signed_close_to_close_lagged
```

## CLI

The CLI accepts:

```bash
--execution-semantics legacy_close_to_close_lagged
--execution-semantics signed_close_to_close_lagged
```

The main intended use case is:

```bash
python3 -m alphaforge.cli research-validate \
  --strategy custom_signal \
  --signal-file path/to/v02_signal.csv \
  --execution-semantics signed_close_to_close_lagged \
  ...
```

## Boundary

This phase does not change the default runtime. Existing commands remain legacy long/flat unless the signed runtime is explicitly requested.
