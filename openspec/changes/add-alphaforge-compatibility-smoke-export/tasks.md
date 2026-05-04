## 1. Package export implementation

- [ ] 1.1 Add a deterministic AlphaForge compatibility smoke-package export helper in the export layer.
- [ ] 1.2 Build smoke-package metadata writers for `signal_contract.yaml`, `data_quality_report.json`, `manifest.json`, and `README.md`.
- [ ] 1.3 Ensure the export helper validates package alignment, row counts, and file integrity without importing AlphaForge.

## 2. Example package fixture

- [ ] 2.1 Generate the committed `examples/alphaforge_compatibility/AAPL_20230101_20241231/` package fixture.
- [ ] 2.2 Confirm the fixture contains `market_data.csv`, `signal.csv`, `signal_contract.yaml`, `data_quality_report.json`, `manifest.json`, and `README.md`.
- [ ] 2.3 Verify the fixture is deterministic and self-contained.

## 3. Regression coverage

- [ ] 3.1 Add tests for package directory creation and required files.
- [ ] 3.2 Add tests for AlphaForge-compatible OHLCV and signal schema alignment.
- [ ] 3.3 Add tests for README command content, manifest metadata, and AlphaForge import boundaries.

## 4. Validation

- [ ] 4.1 Run pytest and fix any contract regressions.
- [ ] 4.2 Run ruff check and fix style issues.
- [ ] 4.3 Run OpenSpec validation and verify the change is apply-ready.
