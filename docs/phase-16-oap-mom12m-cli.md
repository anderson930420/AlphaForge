# Phase 16 OAP Mom12m CLI

Phase 16 adds a terminal workflow for the deterministic local Mom12m pipeline.

Command:

`python3 -m alphaforge.cli run-oap-mom12m-pipeline --characteristics mom12m.csv --contract mom12m_threshold.yaml --market-data market.csv --signal-output signal.csv --symbol AAA`

The command writes a v0.2 signal CSV and prints a JSON summary with row counts, signal metadata, signed execution semantics, trade count, and final equity.

Boundary: no remote OAP / JKP download, no optimization, no cross-sectional rank, no ML changes, no runtime changes, and no signal schema changes.

Verification:

`PYTHONPATH=src python3 -m pytest tests/test_oap_mom12m_pipeline_cli.py tests/test_oap_mom12m_pipeline.py tests/test_oap_signal_adapter.py tests/test_oap_loader.py tests/test_oap_factor_contract.py -q`

`PYTHONPATH=src python3 -m pytest -q`
