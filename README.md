# AlphaForge

AlphaForge is a research-oriented asset-pricing and strategy-validation project.
It started as a minimal quantitative backtesting engine and now also contains
local adapters for external signal packages and Open Source Asset Pricing-style
firm characteristics.

The current role of AlphaForge is downstream validation: load local market data,
consume built-in strategies or externally generated signals, run deterministic
backtest and validation workflows, and write evidence artifacts. It is not a
live trading system, broker simulator, portfolio optimizer, or complete ML
training platform.

## Current Development Status

Current repository capabilities include:

- standardized OHLCV CSV loading and validation
- moving-average crossover and breakout strategy families
- single-run backtests, grid search, train/test validation, walk-forward
  validation, strategy comparison, and permutation diagnostics
- JSON, CSV, and optional HTML output artifacts under `outputs/`
- TWSE daily data fetch helpers
- `custom_signal` consumption for externally generated `signal.csv` files
- SignalForge v0.2 package validation/smoke testing through file artifacts
- local OAP/Open Source Asset Pricing characteristic adapters and Mom12m smoke
  workflows

Recent OAP work has produced local processed feature and signal artifacts from a
private Open Source Asset Pricing raw dataset. Those files are generated local
artifacts and must not be committed.

## Architecture / Pipeline Overview

The main research flow is:

```text
local data or external signal package
        -> schema validation / normalization
        -> strategy or custom_signal target positions
        -> lagged close-to-close backtest
        -> metrics, evidence, reports, and stored artifacts
```

For OAP-style asset-pricing work, the intended flow is:

```text
raw OAP characteristics
        -> local processed feature panels
        -> standardized AlphaForge signal/features
        -> return or market-data join when available
        -> backtest, validation, or future supervised ML
```

OAP characteristics are predictors/features. They are not returns. Full
supervised learning or full historical backtesting still needs market data or
return labels such as `asset_id`, `date`, and `return` or `ret_next_month`.

## Data Model

### Market Data

Standard backtest inputs use one-symbol OHLCV data:

```text
datetime
open
high
low
close
volume
symbol        # optional in some paths, required for custom_signal symbol checks
```

### Signal Schema

AlphaForge supports two external `custom_signal` file shapes.

The older v0.1 long/flat shape is:

```text
datetime
available_at
symbol
signal_name
signal_value
signal_binary
source
```

`signal_binary` maps to target position `1.0` or `0.0`; `signal_value` is
validated but not used for execution.

The newer v0.2 signed long/flat/short shape is:

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

`target_weight` is the execution input and must be within `[-1.0, 1.0]`.
SignalForge v0.2 package smoke tests require
`signed_close_to_close_lagged` execution semantics.

### Feature Schema

Standardized AlphaForge feature panels use:

```text
asset_id
date
<feature columns>
```

For the local OAP monthly files, `date` is the month-end date converted from
raw `yyyymm`.

### Return / Label Schema

Returns and supervised-learning labels are separate from characteristics:

```text
asset_id
date
return
ret_next_month    # common supervised target, not present in OAP characteristics
```

The current OAP characteristic files do not provide future returns. Any ML or
backtest workflow that requires labels must join these features to a separate
return or market-data source.

### Backtest Output

Backtest and validation workflows write artifacts such as:

```text
metrics_summary.json
equity_curve.csv
trade_log.csv
ranked_results.csv
validation_summary.json
walk_forward_summary.json
permutation_test_summary.json
```

## OAP Data Integration

The local raw dataset currently prepared on this machine is from Open Source
Asset Pricing:

```text
data/raw/oap/signed_predictors_dl_wide.zip
data/raw/oap/signed_predictors_dl_wide.csv
```

The raw CSV has been verified locally with:

- `211` columns
- identifier columns `permno` and `yyyymm`
- `209` firm-level characteristic columns
- important characteristics present: `Mom12m`, `BM`, `AssetGrowth`, `Beta`,
  `OperProf`, and `Investment`

These raw files are private/local data and are intentionally ignored by git.
AlphaForge does not include an OAP downloader.

### Processed Local OAP Files

Current generated files under `data/processed/oap/` include:

```text
oap_mom12m.csv
oap_mom12m_signal.csv
oap_mom12m_signal.parquet
oap_panel_2010_2012_selected.csv
oap_panel_2010_2012_features.csv
oap_panel_2010_2012_features.parquet
```

`oap_mom12m.csv` contains:

```text
permno
yyyymm
Mom12m
```

The observed non-null row count is `3,715,128`.

`oap_mom12m_signal.parquet` is the preferred local processed format for the
standardized single-signal file:

```text
shape: (3715128, 3)
asset_id: int64
date: datetime64[us]
signal: float64
```

Sample rows begin with `asset_id=10000`, `date=1986-12-31`, and
`signal=-0.810714`.

`oap_panel_2010_2012_features.parquet` is the preferred local processed format
for the selected multi-feature panel:

```text
shape: (255258, 8)
asset_id: int64
date: datetime64[us]
AssetGrowth: float64
BM: float64
Beta: float64
Investment: float64
Mom12m: float64
OperProf: float64
```

The CSV companion files are useful for inspection, but the Parquet files are the
preferred local loader format because they preserve the parsed `date` dtype.

### Missingness Caveat

Missing values are expected in firm-level characteristics and should be handled
by feature engineering or ML code. They are not, by themselves, evidence that the
OAP files are corrupted.

Observed missingness in the selected 2010-2012 panel:

- `OperProf`: about `72.8%`
- `BM`: about `52.1%`
- `Investment`: about `43.5%`
- `Mom12m`: about `42.1%`
- `AssetGrowth`: about `34.5%`
- `Beta`: about `14.4%`

### Manual OAP Preparation

There is no repository-managed OAP download command. If you already have the
raw file, place it locally under `data/raw/oap/` and keep it out of git.

The raw OAP CSV is large, so avoid reading the full file into memory with a plain
`pd.read_csv(...)`. Prefer selecting only the columns you need and processing the
file in chunks.

Example: build a small 2010-2012 selected feature panel from the raw OAP file:

```python
import pandas as pd

src = "data/raw/oap/signed_predictors_dl_wide.csv"
out = "data/processed/oap/oap_panel_2010_2012_features.parquet"

usecols = [
    "permno",
    "yyyymm",
    "Mom12m",
    "BM",
    "AssetGrowth",
    "Beta",
    "OperProf",
    "Investment",
]

chunks = []

for chunk in pd.read_csv(src, usecols=usecols, chunksize=500_000):
    chunk = chunk[(chunk["yyyymm"] >= 201001) & (chunk["yyyymm"] <= 201212)]

    if not chunk.empty:
        chunks.append(chunk)

frame = pd.concat(chunks, ignore_index=True)

frame = frame.rename(columns={"permno": "asset_id"})
frame["date"] = (
    pd.to_datetime(frame["yyyymm"].astype(str), format="%Y%m")
    + pd.offsets.MonthEnd(0)
)

frame = frame.drop(columns=["yyyymm"])

frame.to_parquet(out, index=False)

print("saved:", out)
print("shape:", frame.shape)
print(frame.dtypes)
```

For generated feature panels, keep the convention:

```text
asset_id,date,<feature columns>
```

For generated single-signal files, keep the convention:

```text
asset_id,date,signal
```

OAP characteristics are predictors/features. They are not realized returns or
future returns. Any full backtest or supervised ML workflow must join these
features to a separate market-data or return-label source.

## OAP Multi-Factor Signal Builder

AlphaForge can combine multiple OAP-style feature columns into a single
`signal.csv` using a YAML configuration. This does not require CRSP or WRDS
data and does not perform ML training. It is a deterministic cross-sectional
ranking and weighting step.

The configuration file specifies:

```yaml
version: alphaforge_oap_multifactor_v0.1
signal_name: oap_multifactor_score
date_col: date
asset_id_col: asset_id
features:
  - name: Mom12m
    weight: 1.0
    higher_is_better: true
  - name: BM
    weight: 1.0
    higher_is_better: true
  - name: Investment
    weight: 1.0
    higher_is_better: false
long_quantile: 0.8
short_quantile: 0.2
gross_long_weight: 1.0
gross_short_weight: -1.0
missing_policy: ignore_feature
normalization: zscore_by_date
```

Per date, each feature is z-score normalized across assets. If `higher_is_better:
false`, the normalized value is inverted. A weighted average is computed and
assets at or above `long_quantile` receive the long target weight; assets at
or below `short_quantile` receive the short target weight; others receive
neutral.

Example CLI usage:

```bash
PYTHONPATH=src python3 -m alphaforge.cli build-oap-multifactor-signal \
  --features data/processed/oap/oap_panel_2010_2012_features.parquet \
  --config tests/fixtures/oap_multifactor/equal_weight.yaml \
  --output artifacts/phase21/oap_multifactor_signal.csv
```

The output is compatible with the AlphaForge `custom_signal` v0.2 contract:

```text
datetime,available_at,symbol,asset_id,signal_name,score,direction,target_weight,source
```

This step only builds a signal file from local features. It does not require
CRSP/WRDS data and does not evaluate performance.

## Return Label Builder

AlphaForge can convert a local monthly return panel into forward return labels for
future supervised learning and OAP/CRSP evaluation. This does not download CRSP
data, require WRDS access, or implement ML training.

The input panel uses:

```text
asset_id,date,ret
```

The output labels use:

```text
asset_id,date,target_date,horizon_months,ret_fwd_1m,source
```

`target_date` is computed as `date + MonthEnd(horizon_months)` using calendar
month-end alignment so that missing months do not silently become multi-month
forward returns.

Example CLI usage:

```bash
PYTHONPATH=src python3 -m alphaforge.cli build-return-labels \
  --returns data/processed/returns/monthly_returns.csv \
  --output artifacts/phase22/return_labels.csv \
  --asset-id-col asset_id \
  --date-col date \
  --return-col ret \
  --horizon-months 1
```

For delisting returns, use `--delisting-return-col dlret` to combine:

```python
combined_return = (1 + ret) * (1 + dlret) - 1
```

This step only builds deterministic forward-return labels. It does not train ML
models, evaluate strategy performance, or connect to WRDS.

## SignalForge Integration

AlphaForge consumes SignalForge artifacts through files. It does not import
SignalForge internals or call SignalForge APIs.

The v0.2 package smoke path expects a package directory containing:

```text
market_data.csv
signal.csv
signal_contract.yaml
data_quality_report.json
manifest.json
README.md
```

AlphaForge validates the package manifest, validates compatibility fragments in
`signal_contract.yaml`, loads `signal.csv` through the `custom_signal` v0.2
loader, and runs a signed long/short smoke backtest.

SignalForge owns signal generation. AlphaForge is the downstream consumer for
schema validation, signed lagged backtesting, evidence generation, and
optimization/validation workflows that operate on AlphaForge-native strategies.
For `custom_signal`, AlphaForge treats the supplied signal as frozen external
input and does not perform parameter search over SignalForge internals.

## ML Roadmap / Current ML Direction

The current codebase has OAP feature preparation and signal/backtest plumbing,
but it does not yet contain a formal supervised ML training pipeline.

The near-term ML direction is:

- treat OAP characteristics as monthly predictors
- join predictors to future return labels from a separate data source
- keep features, signals, labels, and backtest outputs as separate schemas
- add missing-value handling, cross-sectional normalization, train/test splits,
  and model evaluation before treating any model output as a tradable signal

Do not treat `Mom12m`, `BM`, `Beta`, or other OAP characteristics as realized or
future returns.

## CLI Usage

Install locally first:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

After installation, commands can be run as either:

```bash
python -m alphaforge.cli --help
alphaforge --help
```

When running directly from a checkout without installing, use:

```bash
PYTHONPATH=src python3 -m alphaforge.cli --help
```

### Built-In Strategy Examples

Run one moving-average crossover backtest:

```bash
PYTHONPATH=src python3 -m alphaforge.cli run \
  --data sample_data/sample_ohlcv.csv \
  --symbol SAMPLE \
  --short-window 2 \
  --long-window 4
```

Run a parameter search:

```bash
PYTHONPATH=src python3 -m alphaforge.cli search \
  --data sample_data/sample_ohlcv.csv \
  --symbol SAMPLE \
  --short-windows 2 3 \
  --long-windows 4 5 \
  --experiment-name sample_search
```

Run train/test validation:

```bash
PYTHONPATH=src python3 -m alphaforge.cli validate-search \
  --data sample_data/sample_ohlcv.csv \
  --symbol SAMPLE \
  --split-ratio 0.7 \
  --short-windows 2 3 \
  --long-windows 4 5 \
  --experiment-name sample_validation
```

Run walk-forward validation:

```bash
PYTHONPATH=src python3 -m alphaforge.cli walk-forward \
  --data sample_data/sample_ohlcv.csv \
  --symbol SAMPLE \
  --train-size 6 \
  --test-size 3 \
  --step-size 3 \
  --short-windows 2 3 \
  --long-windows 4 5 \
  --experiment-name sample_walk_forward
```

Run a fixed-candidate permutation diagnostic:

```bash
PYTHONPATH=src python3 -m alphaforge.cli permutation-test \
  --data sample_data/sample_ohlcv.csv \
  --symbol SAMPLE \
  --short-window 2 \
  --long-window 4 \
  --permutations 100 \
  --block-size 5 \
  --target-metric score \
  --seed 42
```

### OAP Commands

Convert a local characteristic CSV with `asset_id`, `date`, and one
non-missing characteristic into v0.2 `signal.csv`. The current CLI rejects
missing scores, so either impute upstream or pass a filtered file:

```bash
python3 - <<'PY'
import pandas as pd

cols = ["asset_id", "date", "BM"]
frame = pd.read_csv("data/processed/oap/oap_panel_2010_2012_features.csv", usecols=cols)
frame = frame.dropna(subset=["BM"])
frame.to_csv("outputs/oap_bm_non_missing.csv", index=False)
PY
```

```bash
PYTHONPATH=src python3 -m alphaforge.cli build-oap-signal \
  --input outputs/oap_bm_non_missing.csv \
  --output outputs/oap_bm_signal.csv \
  --characteristic BM \
  --date-col date \
  --asset-id-col asset_id
```

Run the local Mom12m pipeline smoke. This command requires a local market-data
CSV; the OAP characteristic file alone is not enough for a backtest.

```bash
PYTHONPATH=src python3 -m alphaforge.cli run-oap-mom12m-pipeline \
  --characteristics path/to/mom12m_characteristics.csv \
  --contract tests/fixtures/oap_factor_contracts/mom12m_threshold.yaml \
  --market-data path/to/market_data.csv \
  --signal-output outputs/oap_mom12m_signal.csv \
  --symbol AAA
```

A verified fixture smoke for this command produced:

```text
status: passed
signal_rows: 3
trade_count: 2
execution_semantics: signed_close_to_close_lagged
final_equity: 1299.9999999999998
```

There is also a module CLI for writing a local OAP Mom12m JSON report:

```bash
PYTHONPATH=src python3 -m alphaforge.oap_real_data_cli \
  --characteristics path/to/mom12m_characteristics.csv \
  --contract tests/fixtures/oap_factor_contracts/mom12m_threshold.yaml \
  --market-data path/to/market_data.csv \
  --signal-output outputs/oap_mom12m_signal.csv \
  --report-output outputs/oap_mom12m_report.json \
  --symbol AAA
```

### SignalForge Commands

Smoke-test the checked-in SignalForge v0.2 sample package:

```bash
PYTHONPATH=src python3 -m alphaforge.cli smoke-signalforge-package \
  --package sample_data/signalforge/demo_v02_package
```

The sample package smoke currently returns `status: passed`,
`signal_contract_version: v0.2`, `target_position_source_column:
target_weight`, `execution_semantics: signed_close_to_close_lagged`, and
`trade_count: 2`.

Run `custom_signal` research validation against a v0.1 SignalForge-style
fixture:

```bash
PYTHONPATH=src python3 -m alphaforge.cli research-validate \
  --strategy custom_signal \
  --data tests/fixtures/signalforge/market_data.csv \
  --symbol SFDEMO \
  --signal-file tests/fixtures/signalforge/signal.csv \
  --signal-name signalforge_v01_momentum \
  --development-start 2025-01-02 \
  --development-end 2025-01-08 \
  --holdout-start 2025-01-09 \
  --holdout-end 2025-01-13 \
  --train-size 3 \
  --test-size 2 \
  --step-size 1
```

For v0.2 signed custom signals, pass signed execution semantics:

```bash
PYTHONPATH=src python3 -m alphaforge.cli research-validate \
  --strategy custom_signal \
  --execution-semantics signed_close_to_close_lagged \
  --data path/to/market_data.csv \
  --symbol SFDEMO \
  --signal-file path/to/signal.csv \
  --development-start 2025-01-02 \
  --development-end 2025-01-08 \
  --holdout-start 2025-01-09 \
  --holdout-end 2025-01-13 \
  --train-size 3 \
  --test-size 2 \
  --step-size 1
```

Batch smoke checks for multiple SignalForge v0.2 packages are available as a
script:

```bash
python3 scripts/run_signalforge_batch_package_smoke.py \
  --packages-root path/to/packages \
  --summary-output outputs/signalforge_batch_summary.json
```

## HTML Artifact Reports

Render a standalone HTML report from any AlphaForge artifact directory or OAP
report JSON. The renderer reads whatever artifacts are present and produces a
standalone HTML report file with metric cards, equity/drawdown charts (Plotly),
trade log tables, and summaries.
Charts use Plotly from CDN when opened in a browser.

```bash
PYTHONPATH=src python3 -m alphaforge.cli render-artifact-report \
  --artifact-dir outputs/some_run \
  --output outputs/some_run/report.html
```

For a standalone OAP report JSON (e.g. from ``alphaforge.oap_real_data_cli``):

```bash
PYTHONPATH=src python3 -m alphaforge.cli render-artifact-report \
  --artifact-dir outputs/some_run \
  --output outputs/some_run/oap_report.html \
  --report-json outputs/oap_mom12m_report.json
```

The renderer gracefully reports missing optional files. No CRSP/WRDS data, live
trading, broker execution, external data downloads, or ML training is performed.

## Local Development Setup

Python `>=3.11` is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows, use the local Python launcher that exists on the machine. If
`python` is unavailable, try `python3`, and vice versa.

The local memory/logger workflow uses `scripts/read_memory.py` and
`src/obsidian_logger.py`; those files are machine-local and ignored by git.

## Testing / Smoke Tests

Run the full test suite:

```bash
PYTHONPATH=src python3 -m pytest -q
```

Focused smoke checks:

```bash
PYTHONPATH=src python3 -m pytest tests/test_oap_mom12m_pipeline_cli.py -q
PYTHONPATH=src python3 -m pytest tests/test_signalforge_package_cli.py -q
PYTHONPATH=src python3 -m pytest tests/test_oap_signal_cli.py -q
```

There is no README-specific lint configured in this repository.

## Data Privacy And Git Hygiene

Do not commit local datasets or generated research artifacts.

The following patterns must stay ignored:

```text
artifacts/
data/raw/
data/processed/
data/**/*.csv /
data/**/*.zip /
data/**/*.parquet
outputs/
```

This is especially important for:

```text
data/raw/oap/signed_predictors_dl_wide.zip
data/raw/oap/signed_predictors_dl_wide.csv
data/processed/oap/*.csv
data/processed/oap/*.parquet
```

The repository contains small checked-in sample CSVs under `sample_data/` and
`tests/fixtures/` for deterministic tests. Do not use that as permission to add
large raw or processed datasets.

## Current Limitations

- no bundled OAP downloader
- no committed OAP raw or processed data
- no formal supervised ML trainer yet
- no return-label generation from OAP characteristics
- no claim that OAP characteristics contain future returns
- current `custom_signal` validation is primarily one-symbol at runtime
- SignalForge integration is file-based; AlphaForge does not import SignalForge
- OAP-related code uses some OAP / JKP-style contract language, but the local
  raw dataset documented here is the Open Source Asset Pricing file above, not a
  separate committed JKP stock-level dataset

## Near-Term Roadmap

- formalize local loaders for the processed OAP Parquet feature and signal files
- add explicit feature/label joins once return data is available
- define missing-value and cross-sectional normalization policies for ML inputs
- keep SignalForge package compatibility checks aligned with the v0.2 contract
- preserve strict data hygiene so private raw and processed datasets remain out
  of git
