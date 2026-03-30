# AlphaForge

AlphaForge is a minimal strategy research engine that proves a reproducible MVP pipeline:

`strategy spec -> backtest -> metrics -> ranking -> save result`

## MVP Status

The current MVP supports:

- Loading standardized OHLCV CSV data
- Running a baseline moving average crossover strategy
- Executing a simple single-asset backtest
- Computing Sharpe, max drawdown, win rate, turnover, trade count, and return metrics
- Searching multiple MA parameter combinations and ranking them
- Saving experiment outputs as JSON and CSV
- Fetching TWSE stock-day data into the same standardized CSV format
- Running everything from a CLI
- Running a simple train/test validation workflow for parameter search
- Running a first-pass walk-forward validation workflow for parameter search

Deferred capabilities such as paper parsing, formula extraction, genetic algorithms, broker integration, live trading, and web UI remain intentionally out of scope.

## Project Layout

```text
src/alphaforge/
  config.py
  schemas.py
  data_loader.py
  backtest.py
  metrics.py
  scoring.py
  search.py
  experiment_runner.py
  storage.py
  twse_client.py
  cli.py
  strategy/
tests/
sample_data/
outputs/
scripts/
```

## Setup

Create a virtual environment and install the project in editable mode with dev dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

If `.venv` already exists but is broken because its base interpreter path no longer exists, rebuild it with a known-good Python installation:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\rebuild_venv.ps1 -PythonExe "C:\path\to\python.exe"
```

## CLI Usage

Run a single MA crossover experiment from a CSV:

```powershell
.venv\Scripts\python.exe -m alphaforge.cli run --data .\sample_data\sample_ohlcv.csv --symbol SAMPLE --short-window 2 --long-window 4
```

Run a parameter search from a CSV:

```powershell
.venv\Scripts\python.exe -m alphaforge.cli search --data .\sample_data\sample_ohlcv.csv --symbol SAMPLE --short-windows 2 5 10 --long-windows 20 40 60 --experiment-name sample_search
```

Run a train/test validation search from a CSV:

```powershell
.venv\Scripts\python.exe -m alphaforge.cli validate-search --data .\sample_data\sample_ohlcv.csv --symbol SAMPLE --short-windows 2 5 10 --long-windows 20 40 60 --split-ratio 0.7 --experiment-name sample_validation
```

Run a walk-forward validation search from a CSV:

```powershell
.venv\Scripts\python.exe -m alphaforge.cli walk-forward --data .\sample_data\sample_ohlcv.csv --symbol SAMPLE --short-windows 2 5 10 --long-windows 20 40 60 --train-size 120 --test-size 20 --step-size 20 --experiment-name sample_walk_forward
```

Search output now returns a compact summary payload with:

- `result_count`
- `best_result`
- `top_results`
- `ranked_results_path`
- `report_path` when `--generate-report` creates `best_report.html`
- `search_report_path` when `--generate-report` creates `search_report.html`

Fetch TWSE daily data to a standardized CSV:

```powershell
.venv\Scripts\python.exe -m alphaforge.cli fetch-twse --stock-no 2330 --start-month 2024-01 --end-month 2024-03 --output .\sample_data\twse_2330_2024q1.csv
```

Fetch TWSE data and immediately run parameter search:

```powershell
.venv\Scripts\python.exe -m alphaforge.cli twse-search --stock-no 2330 --start-month 2024-01 --end-month 2024-03 --data-output .\sample_data\twse_2330_2024q1.csv --output-dir .\outputs --experiment-name twse_2330_search --short-windows 5 10 15 --long-windows 20 40 60
```

## Output Structure

Single experiment outputs:

```text
outputs/<experiment_name>/
  experiment_config.json
  metrics_summary.json
  trade_log.csv
  equity_curve.csv
```

Search outputs:

```text
outputs/<search_name>/
  ranked_results.csv
  best_report.html          # when --generate-report is used and ranked results exist
  search_report.html        # when --generate-report is used
  runs/
    run_001/
    run_002/
    ...
```

Validation outputs:

```text
outputs/<validation_name>/
  validation_summary.json
  train_search/
    ranked_results.csv
    runs/
      run_001/
      run_002/
      ...
  test_selected/
    experiment_config.json
    metrics_summary.json
    trade_log.csv
    equity_curve.csv
```

Walk-forward outputs:

```text
outputs/<walk_forward_name>/
  walk_forward_summary.json
  fold_results.csv
  folds/
    fold_001/
      train_search/
      test_selected/
    fold_002/
      train_search/
      test_selected/
    ...
```

## Verification

Run the repo-local verification script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_verification.ps1
```

This runs `pytest` and one CLI smoke test using `sample_data/sample_ohlcv.csv`.

Focused examples:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_cli.py -q
.venv\Scripts\python.exe -m pytest tests\test_runner.py -q
.venv\Scripts\python.exe -m pytest tests\test_twse_client.py -q
```

## Current Success Criteria

The MVP is considered successful when it can:

- Load a standardized dataset
- Run MA crossover backtests
- Output Sharpe, max drawdown, win rate, and turnover
- Evaluate and rank multiple parameter sets
- Save results for later inspection
