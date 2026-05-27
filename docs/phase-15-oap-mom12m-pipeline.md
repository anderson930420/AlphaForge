# Phase 15 OAP Mom12m Pipeline

Phase 15 adds the first deterministic Mom12m pipeline smoke.

The pipeline connects local characteristics CSV input, the OAP factor contract, the OAP loader, the OAP signal adapter, signal.csv v0.2, the custom_signal loader, and the signed AlphaForge backtest runtime.

Changed files include the new `alphaforge.oap_mom12m_pipeline` module and deterministic pipeline tests.

This phase does not download remote data. It does not add optimization, cross-sectional ranking, ML behavior, runtime semantic changes, or v0.2 signal schema changes.

Verification:

`PYTHONPATH=src python3 -m pytest tests/test_oap_mom12m_pipeline.py tests/test_oap_signal_adapter.py tests/test_oap_loader.py tests/test_oap_factor_contract.py -q`

`PYTHONPATH=src python3 -m pytest -q`
