請先閱讀 AGENT.md 並遵守。
接著幫我完成這個專案的下一步。

You are acting as a senior Python architect and quant research infrastructure engineer.

Your job is NOT to build a full autonomous AI trading platform.
Your job is to define and implement the minimum viable version (MVP) of a project called AlphaForge.

You must follow the architecture-first style:
1. first define module responsibilities and system boundaries,
2. then create the minimal implementation,
3. then add tests,
4. then verify the pipeline end-to-end.

Do not bloat the scope.
Do not introduce unnecessary abstractions.
Do not add features that are not explicitly requested.

================================
PROJECT GOAL
================================

AlphaForge MVP is a reproducible strategy research engine.

The MVP only needs to prove this pipeline works:

strategy spec -> backtest -> metrics -> ranking -> save result

This MVP is NOT yet about:
- paper parsing
- formula extraction from papers
- multi-agent orchestration
- genetic algorithms
- live trading
- broker API integration
- fancy UI
- Streamlit dashboard

Those are future phases, not this implementation.

================================
MVP SCOPE
================================

Build a Python project that can:

1. load standardized OHLCV market data
2. run one baseline strategy: moving average crossover
3. execute a backtest
4. compute key performance metrics
5. compare multiple parameter sets
6. rank results
7. save experiment outputs for later inspection
8. expose everything through a CLI
9. include tests for the core logic

Use Python as the implementation language.

================================
ARCHITECTURE REQUIREMENTS
================================

Create or update the project so it has these modules with clear responsibilities:

- config.py
  Centralized defaults, parameter ranges, fees, slippage, initial capital, random seed, output paths

- schemas.py
  Shared data contracts / dataclasses / typed structures for:
  DataSpec
  StrategySpec
  BacktestConfig
  TradeRecord
  MetricReport
  ExperimentResult

- data_loader.py
  Load CSV market data
  Standardize columns:
  datetime, open, high, low, close, volume
  Sort data
  Remove duplicates
  Define a clear missing-data policy
  Validate schema assumptions

- strategy/base.py
  Define the common strategy interface

- strategy/ma_crossover.py
  Implement a baseline moving average crossover strategy
  Output a signal or target position series

- backtest.py
  Convert strategy output into positions, trades, and equity curve
  Include fee and slippage handling
  Keep implementation simple and auditable

- metrics.py
  Compute at least:
  total return
  annualized return or CAGR
  Sharpe ratio
  max drawdown
  win rate
  turnover
  trade count

- scoring.py
  Define ranking logic for experiment results
  Support filtering by thresholds such as:
  max drawdown cap
  minimum trade count
  Then compute a final score for ranking

- search.py
  Implement parameter search
  Start with grid search or random search only
  Do NOT implement genetic algorithms yet

- experiment_runner.py
  Orchestrate:
  load data -> build strategy -> run backtest -> compute metrics -> score -> package result

- storage.py
  Save outputs to disk using simple formats such as CSV and JSON
  Save:
  experiment config
  metrics summary
  trade log
  equity curve
  ranked results

- cli.py
  Provide a command-line interface to run:
  single experiment
  parameter search
  output saving

- tests/
  Add focused pytest coverage for:
  data loading assumptions
  MA crossover logic
  backtest consistency
  metric correctness
  end-to-end runner behavior

================================
IMPLEMENTATION CONSTRAINTS
================================

Important constraints:

- Keep the code modular and explicit
- Prefer clarity over cleverness
- Avoid hidden state
- Avoid overengineering
- Do not add a database in this MVP
- Use local file storage only
- Do not add Streamlit yet
- Do not add live/paper trading yet
- Do not add LLM paper parsing yet
- Do not add optimization frameworks beyond simple search
- Do not use overly heavy dependencies unless clearly necessary

Preferred baseline stack:
- Python
- pandas
- numpy
- pytest
- argparse or typer (argparse is fine if simpler)

================================
DESIGN PRINCIPLES
================================

Follow these design principles:

- Each module should have one clear responsibility
- Validation should be separated from strategy logic
- Strategy logic should be separated from backtest execution
- Metrics should be separated from scoring
- Search logic should be separated from experiment execution
- CLI should be a thin orchestration layer
- Outputs must be reproducible and inspectable

================================
EXPECTED FOLDER STRUCTURE
================================

Target structure should be roughly:

alphaforge/
  config.py
  schemas.py
  data_loader.py
  backtest.py
  metrics.py
  scoring.py
  search.py
  experiment_runner.py
  storage.py
  cli.py
  strategy/
    __init__.py
    base.py
    ma_crossover.py
  tests/
    test_data_loader.py
    test_strategy_ma.py
    test_backtest.py
    test_metrics.py
    test_runner.py
  outputs/

Adjust only if the existing repository structure strongly suggests a better equivalent.

================================
EXECUTION PLAN
================================

Follow this order of work:

Phase 1: inspect repository
- inspect the current repo structure
- identify what already exists
- do not blindly overwrite good existing code
- summarize what should be kept, refactored, or added

Phase 2: architecture mapping
- produce a concise module map
- explain responsibility boundaries
- explain what is in MVP and what is deferred

Phase 3: implementation
- implement the missing modules and connect them
- keep interfaces simple and typed where useful

Phase 4: testing
- add pytest tests for critical logic
- prioritize correctness and reproducibility

Phase 5: verification
- run at least one end-to-end example
- confirm outputs are saved correctly
- confirm CLI can run the workflow

================================
OUTPUT STYLE
================================

While working, always:
- explain what you are changing and why
- surface architectural decisions explicitly
- call out any ambiguity before making irreversible changes
- avoid giant monolithic code dumps when smaller coherent edits are better

When you finish, provide:
1. final project structure
2. summary of module responsibilities
3. how to run the CLI
4. how to run tests
5. what is intentionally deferred to later phases

================================
NON-GOALS / DO NOT BUILD YET
================================

Do NOT build these yet:
- paper parser
- PDF ingestion pipeline
- formula extraction agent
- genetic algorithm optimizer
- multi-agent orchestration
- broker API execution
- real-time data streaming
- web UI / Streamlit app
- database layer
- portfolio optimization across many assets

================================
SUCCESS CRITERIA
================================

The MVP is successful if it can:
- load a valid OHLCV dataset
- run MA crossover backtests
- compute Sharpe, max drawdown, win rate, turnover, and total return
- compare multiple parameter sets
- rank them
- save outputs
- pass tests

Start by inspecting the repository and producing the module map before implementing code.

Additional repo-specific instructions:

- Respect the current coding style if the repo already has one.
- Reuse existing utilities when appropriate instead of duplicating logic.
- Do not delete files unless they are clearly obsolete and you explain why.
- Prefer incremental edits over full rewrites.
- Keep the project ready for future extension into:
  paper parsing -> formula strategy generation -> optimizer -> paper/live trading