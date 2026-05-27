# Phase 18 OAP Mom12m Real-Data CLI Report

Phase 18 adds a terminal entrypoint for the local OAP / JKP-style Mom12m real-data report workflow.

## Command

```bash
PYTHONPATH=src python3 -m alphaforge.oap_real_data_cli \
  --characteristics real_mom12m.csv \
  --contract tests/fixtures/oap_factor_contracts/mom12m_threshold.yaml \
  --market-data market.csv \
  --signal-output signal.csv \
  --report-output report.json \
  --symbol AAA
```

## Outputs

The command writes:

```text
signal.csv
report.json
```

It also prints the report summary JSON to stdout.

## Report contents

The report includes:

- input paths
- output signal path
- contract metadata
- factor frame row count and date range
- available_at range
- missing factor value count
- factor value min, max, and mean
- signal direction distribution
- target_weight distribution
- signed backtest summary
- signal metadata

## Boundary

This phase does not download remote data, commit external datasets, add optimization, add cross-sectional rank rules, change ML behavior, change runtime semantics, or change the v0.2 signal schema.

## Verification

```bash
PYTHONPATH=src python3 -m pytest tests/test_oap_real_data_cli.py tests/test_oap_real_data_workflow.py tests/test_oap_mom12m_pipeline_cli.py tests/test_oap_mom12m_pipeline.py tests/test_oap_signal_adapter.py tests/test_oap_loader.py tests/test_oap_factor_contract.py -q
PYTHONPATH=src python3 -m pytest -q
```
