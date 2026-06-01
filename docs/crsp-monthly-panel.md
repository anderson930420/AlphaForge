# CRSP Monthly Panel Adapter

## Goal

Add a thin adapter and QC layer so AlphaForge can read an externally generated
CRSP monthly parquet panel without copying raw CRSP data into the repository.

## Boundary

This phase only reads, validates, filters, and inspects an external monthly
panel. It does not add Compustat linking, factor generation, ML integration,
or backtest changes. The external data path is provided at runtime.

## Expected Schema

AlphaForge expects the canonical monthly panel columns below:

| Column | Meaning |
| --- | --- |
| `date` | Monthly observation date |
| `asset_id` | Stable asset identifier used by AlphaForge |
| `permno` | CRSP security identifier |
| `permco` | CRSP company identifier |
| `ticker` | Ticker symbol |
| `cusip` | CUSIP identifier |
| `ncusip` | Historical CUSIP identifier |
| `exchcd` | CRSP exchange code |
| `shrcd` | CRSP share code |
| `siccd` | CRSP SIC code |
| `price` | Month-end price |
| `ret` | Monthly return |
| `retx` | Monthly return excluding distributions |
| `dlret` | Delisting return |
| `volume` | Trading volume |
| `shares_out` | Shares outstanding |
| `market_cap` | Equity market capitalization |
| `lag_market_cap` | Prior-month market capitalization |
| `total_ret` | Return including delisting return |
| `is_common_share` | Common-share universe flag |
| `is_primary_us_exchange` | Primary US exchange flag |
| `daily_obs_count` | Count of daily observations used to build the month |
| `first_trading_date` | First trading date in the panel span |
| `last_trading_date` | Last trading date in the panel span |

## Validation Rules

`validate_crsp_monthly_panel()` enforces the canonical contract:

- all canonical columns must exist
- `date` must be parseable as datetime
- `asset_id` must be present and non-null
- duplicate `asset_id` / `date` rows are not allowed
- `is_common_share` and `is_primary_us_exchange` must be boolean-like

Missing `ret` values are allowed. CRSP monthly panels can legitimately contain
missing returns, delisting returns, or lagged market-cap values.

## Loader Behavior

`load_crsp_monthly_panel()` reads the external parquet file with
`pandas.read_parquet`, parses `date`, coerces the boolean-like universe flags,
sorts by `asset_id` and `date`, applies optional filters, validates the
filtered result, and returns the canonical monthly column order when
`columns is None`.

Supported filters:

- `start_date`
- `end_date`
- `common_shares_only`
- `primary_exchange_only`

The loader does not write files and does not copy raw CRSP data.

## Inspection Command

Use the standalone inspector to print QC metadata as JSON:

```bash
PYTHONPATH=src python3 scripts/inspect_crsp_monthly_panel.py \
  --input "/Users/anderson930420/Desktop/crsp_parquet/monthly/crsp_monthly_1995_2023.parquet" \
  --qc-output artifacts/crsp_monthly_panel_qc.json
```

Optional filters can be passed on the command line:

- `--start-date`
- `--end-date`
- `--common-shares-only`
- `--primary-exchange-only`

The command prints JSON to stdout and writes the same JSON to `--qc-output` if
provided. It does not print raw rows.

## QC Fields

`build_crsp_monthly_panel_qc()` returns:

- `rows`
- `assets`
- `date_min`
- `date_max`
- `months`
- `duplicate_asset_date_rows`
- `missing_ret_ratio`
- `missing_total_ret_ratio`
- `missing_price_ratio`
- `missing_market_cap_ratio`
- `missing_lag_market_cap_ratio`
- `common_share_rows`
- `primary_exchange_rows`
- `frequency`

## Limitations

- No Compustat linking in this phase
- No factor generation in this phase
- No ML integration in this phase
- No backtest integration in this phase
- External data path is supplied at runtime

## Validation

```bash
PYTHONPATH=src python3 -m pytest tests/test_crsp_monthly_panel.py -q
PYTHONPATH=src python3 -m pytest -q
ruff check
git diff --check
git status --short
```

## Notes

Expected QC on the reference external monthly panel should be close to:

- rows: 1,478,910
- assets: 14,905
- date_min: 1995-01-31
- date_max: 2023-12-31
- months: 348
- duplicate_asset_date_rows: 0
- frequency: monthly
