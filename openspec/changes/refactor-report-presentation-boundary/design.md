# Design: refactor-report-presentation-boundary

## Canonical ownership mapping

- `src/alphaforge/report.py`
  - authoritative for report rendering contracts:
    - report section composition,
    - human-facing tables,
    - report-level links to already-materialized artifacts,
    - rendered report file content
  - not authoritative for artifact schema, metric formulas, benchmark semantics, or runtime result schema
- `src/alphaforge/visualization.py`
  - authoritative for figure-generation contracts:
    - figure input validation that exists only to build charts,
    - plot-ready transformation,
    - figure construction
  - not authoritative for report page composition, CLI payload shape, or persistence schema
- `src/alphaforge/cli.py`
  - authoritative for command-facing output payload assembly:
    - JSON/text payload fields returned by CLI commands,
    - command-level inclusion or omission of optional artifact/report paths
  - not authoritative for report content, figure semantics, or artifact layout
- `src/alphaforge/storage.py`
  - remains authoritative for artifact references, filenames, and directory layout
  - presentation layers may display storage-owned paths, but must not redefine them

## Contract migration plan

- Treat report input contracts as explicit presentation inputs rather than inferred persistence layout:
  - `ExperimentResult`
  - normalized benchmark summaries
  - `ArtifactReceipt`
  - ranked result lists
  - comparison equity-curve payloads
- Treat figure input contracts as explicit visualization inputs rather than implicit runtime/persistence assumptions:
  - equity-curve frames for equity and drawdown figures
  - trade logs for trade-marker figures
  - comparison curve maps for ranked-search comparison figures
- Treat CLI payload contracts as derived presentation outputs:
  - CLI may serialize runtime results and storage-owned artifact refs
  - CLI must not invent parallel artifact naming or report-link rules
- Keep `README.md` advisory-only, but require it to describe the presentation contracts derived from these owners.

## Duplicate logic removal plan

- Remove any report-local assumptions that recompute storage layout from artifact filenames or folder naming when `ArtifactReceipt` or explicit path inputs are available.
- Remove any visualization-local assumptions that effectively redefine runtime or persistence schemas instead of enforcing presentation-only input requirements.
- Remove any CLI-local path construction that duplicates report/storage ownership once a canonical payload contract is chosen.
- Downgrade any README or docstring wording that describes output shape independently of the CLI/report/storage owners.

## Verification plan

- Add or update tests proving:
  - report rendering consumes explicit artifact references rather than runtime-path guessing,
  - visualization validation errors correspond to presentation-only input requirements,
  - CLI output payloads are derived from runtime results plus storage-owned artifact refs,
  - report link rendering does not redefine storage-owned layout.
- Review `report.py`, `visualization.py`, and `cli.py` for:
  - inline filename assumptions,
  - implicit layout inference,
  - duplicate path-shaping logic,
  - presentation code recomputing semantic summaries.

## Temporary migration states

- Temporary state:
  - `report.py` may continue receiving `search_root` plus `ArtifactReceipt` while report-link rendering is tightened.
  - `cli.py` may continue returning direct path strings while the CLI output contract is made explicit.
- Removal trigger:
  - remove transitional layout inference once report inputs and CLI payload fields are fully defined as explicit derived contracts.
