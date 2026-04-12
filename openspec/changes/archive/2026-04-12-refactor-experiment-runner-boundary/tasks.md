# Tasks

## 1. Spec and contract alignment

- [x] 1.1 Align the change-local orchestration spec with the top-level architecture boundary map.
- [x] 1.2 Identify every place in `experiment_runner.py` where schema, path, or report ownership may be duplicated.
- [x] 1.3 Classify every helper in `experiment_runner.py` as `pure orchestration`, `domain execution coordination`, or `non-runner concern`.

## 2. Code migration

- [x] 2.1 Remove any orchestration-local path or artifact-shape logic that belongs to `storage.py`.
- [x] 2.2 Remove any orchestration-local analytics or benchmark logic that belongs to `metrics.py` or `benchmark.py`.
- [x] 2.3 Keep only workflow protocol guards, sequencing, strategy dispatch, and workflow metadata assembly inside `experiment_runner.py`.
- [x] 2.4 Extract report-input loading and search-report helper logic so runner keeps sequencing ownership without owning report input shape.
- [x] 2.5 Extract walk-forward aggregate-result and benchmark-summary shaping out of runner if those semantics are intended to outlive the workflow module.
- [x] 2.6 Re-evaluate whether the `(ExperimentResult, EquityCurveFrame, pd.DataFrame, ArtifactReceipt | None)` pairing should be wrapped in a thin execution-output contract after the non-runner helpers are removed.

## 3. Verification

- [x] 3.1 Add or update tests for search, validation, and walk-forward workflows that prove orchestration stays downstream of storage and schema ownership.
- [x] 3.2 Add or update tests for report workflow behavior that prove report content still comes from `report.py`.
- [x] 3.3 Add or update tests proving runner no longer loads artifact data or formats report labels outside the extracted boundary.

## 4. Cleanup

- [x] 4.1 Delete stale helpers or duplicate assumptions that conflict with the orchestration-only boundary.
- [x] 4.2 Update architecture notes or docstrings only after code ownership matches the new spec.
