# Design

## Overview

The MVP comparison layer wraps the existing validation-search workflow once per supported strategy family. Each family receives its own search space, validation output directory, selected train candidate, test rerun, optional permutation diagnostic, and research-policy decision.

The comparison unit is the best validated candidate per family. The workflow does not flatten MA and breakout parameter candidates into one shared grid.

## Boundaries

- `cli.py` parses `compare-strategies` arguments and assembles config objects only.
- `experiment_runner.py` exposes the public comparison entrypoint and return bundle.
- `runner_workflows.py` coordinates the comparison loop and delegates each family to the existing validation-search workflow.
- `schemas.py` owns runtime comparison dataclasses.
- `storage.py` owns comparison artifact filenames, persisted JSON/CSV shape, and path receipts.
- `scoring.py` remains the owner of candidate score computation.
- `research_policy.py` remains the owner of research-policy verdicts.
- `permutation.py` remains the owner of permutation/null diagnostic semantics.

## Workflow

1. Validate the requested strategy family names.
2. Materialize a comparison root at `output_dir / experiment_name` when persistence is requested.
3. For each strategy family:
   - build that family's parameter grid from its `StrategyFamilySearchConfig`;
   - call the existing validation-search workflow with shared data, split, backtest, threshold, policy, and permutation configs;
   - persist the family under `strategies/<strategy_name>/`;
   - normalize the validation output into a comparison result row.
4. Sort comparison results by research-policy verdict group, then descending test score.
5. Persist `comparison_summary.json` and `comparison_results.csv`.

## Ranking

Comparison ordering is:

1. research-policy `promote`
2. research-policy `blocked`
3. research-policy `reject`
4. missing/unknown verdicts

Within each group, results are sorted by descending test score. The ordering is advisory only and never changes the per-family research-policy verdict.

## Failure Behavior

The MVP is fail-fast. Unsupported families, empty search results, validation failures, and invalid parameter grids fail the whole comparison run. This avoids producing misleading comparison rows with fake metrics.

## Artifact Layout

The comparison root is `output_dir / experiment_name`. The MVP layout is:

```text
alphaforge_run/
  comparison_summary.json
  comparison_results.csv
  strategies/
    ma_crossover/
      validation_summary.json
      train_ranked_results.csv
      policy_decision.json
      train_best/
      test_selected/
      permutation_test/
    breakout/
      validation_summary.json
      train_ranked_results.csv
      policy_decision.json
      train_best/
      test_selected/
      permutation_test/
```

`permutation_test/` exists only when permutation evidence is enabled and successfully persisted by the existing validation workflow.
