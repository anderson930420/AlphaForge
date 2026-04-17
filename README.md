# AlphaForge

AlphaForge is a minimal strategy research engine that proves a reproducible MVP pipeline:

`strategy spec -> candidate search -> backtest -> metrics -> scoring -> storage/report`

The canonical contract and boundary details live in `openspec/specs/...`; this README is a practical usage overview, not the source of truth for ownership or workflow semantics.

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
- Comparing strategy results against a buy-and-hold baseline in reports and validation summaries

Deferred capabilities such as paper parsing, formula extraction, genetic algorithms, broker integration, live trading, and web UI remain intentionally out of scope.

## Project Layout

```text
src/alphaforge/
  config.py
  schemas.py
  benchmark.py
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

### Moving To Another Machine

Keep secrets and machine-local state out of GitHub. This repo already ignores:

- `.env`
- `.venv/`
- `outputs/`

Use this workflow when moving the project to another machine such as a MacBook:

1. Push the repo to GitHub without `.env`, `.venv`, or generated outputs.
2. Clone the repo on the new machine.
3. Create a fresh virtual environment on that machine.
4. Copy `.env.example` to `.env`.
5. Fill the required local secrets back into `.env`.

Current required `.env` values:

- `API_KEY`: used by `src/obsidian_logger.py` and `scripts/read_memory.py` for the local Obsidian REST bridge.

Example on macOS:

```bash
cd /path/to/AlphaForge
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

Then edit `.env` and replace the placeholder value with your real local key before running any logger or memory scripts.

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

- `strategy_name`
- `search_parameter_names`
- `attempted_combinations`
- `valid_combinations`
- `invalid_combinations`
- `result_count`
- `ranking_score`
- `best_result`
- `top_results`
- `ranked_results_path`
- `report_path` when `--generate-report` creates `best_report.html`
- `search_report_path` when `--generate-report` creates `search_report.html`

Validation output now surfaces:

- `candidate_evidence`
- `validation_summary_path`
- `train_ranked_results_path`

Walk-forward output now surfaces:

- `walk_forward_evidence`
- `walk_forward_summary_path`
- `fold_results_path`

Report rendering now uses explicit presentation inputs:

- single-experiment HTML reports consume a prepared report input bundle instead of inferring benchmark presentation data internally
- search comparison reports render relative links from an explicit link context instead of guessing layout from workflow paths

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

Single-experiment HTML reports include strategy-versus-buy-and-hold comparison alongside the existing strategy equity, drawdown, and price/trade views.

Migration note:

- `ExperimentResult` no longer carries persisted artifact paths.
- Persisted artifact references now live in storage-owned `ArtifactReceipt` payloads.
- New callers and integrations should be receipt-first and should not treat runtime result objects as artifact locators.

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
  train_ranked_results.csv
  train_best/
    experiment_config.json
    metrics_summary.json
    trade_log.csv
    equity_curve.csv
  test_selected/
    experiment_config.json
    metrics_summary.json
    trade_log.csv
    equity_curve.csv
```

`validation_summary.json` includes the selected strategy test result plus a test-side `test_benchmark_summary` for buy-and-hold comparison.

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

`walk_forward_summary.json` and `fold_results.csv` include buy-and-hold benchmark summaries for each test fold.

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
