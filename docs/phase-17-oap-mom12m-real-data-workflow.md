# Phase 17 OAP Mom12m Real-Data Local Workflow

Phase 17 adds a local reporting workflow for running user-provided OAP / JKP-style Mom12m CSV files without committing or downloading external data.

The workflow wraps the existing Phase 15 pipeline and produces a JSON-serializable summary for local inspection.

## Flow

```text
local characteristics CSV
local market data CSV
Mom12m contract
signal.csv v0.2 output
signed AlphaForge backtest smoke
JSON report summary
```

## Added module

```text
alphaforge.oap_real_data_workflow
```

Main function:

```python
run_oap_mom12m_real_data_local_workflow(...)
```

It returns:

```python
OAPMom12mRealDataWorkflowResult
```

## Report contents

The summary includes:

- input paths
- signal output path
- contract version and rule metadata
- factor row count
- symbol count
- raw factor date range
- available_at date range
- missing factor value count
- factor value min, max, and mean
- signal row count
- direction distribution
- target_weight distribution
- signed backtest summary
- signal metadata

## Boundary

This phase does not commit OAP / JKP data, download remote data, add optimization, add cross-sectional ranking, change ML behavior, change runtime semantics, or change the v0.2 signal schema.

## Verification

```bash
PYTHONPATH=src python3 -m pytest tests/test_oap_real_data_workflow.py tests/test_oap_mom12m_pipeline_cli.py tests/test_oap_mom12m_pipeline.py tests/test_oap_signal_adapter.py tests/test_oap_loader.py tests/test_oap_factor_contract.py -q
PYTHONPATH=src python3 -m pytest -q
```
