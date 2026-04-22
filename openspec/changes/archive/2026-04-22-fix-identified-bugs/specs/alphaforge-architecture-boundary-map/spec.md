# Delta for AlphaForge Architecture Boundary Map

## ADDED Requirements

### Requirement: `metrics.py` owns excess-return Sharpe semantics with a per-period risk-free input

`src/alphaforge/metrics.py` SHALL remain the canonical owner of Sharpe-ratio semantics, including subtraction of a caller-supplied per-period `risk_free_rate` before annualization.

#### Purpose

- Keep performance analytics semantics centralized in `metrics.py`.
- Make it explicit that Sharpe uses excess per-period returns while preserving backward compatibility for existing callers.

#### Canonical owner

- `src/alphaforge/metrics.py` is the authoritative owner of Sharpe-ratio calculation semantics.
- `src/alphaforge/runner_workflows.py`, `src/alphaforge/permutation.py`, `src/alphaforge/report.py`, `src/alphaforge/storage.py`, and `src/alphaforge/cli.py` are downstream consumers of the computed metric values only.

#### Allowed responsibilities

- `metrics.py` MAY accept `risk_free_rate: float = 0.0` on `compute_metrics()` and `_compute_sharpe_ratio()`.
- `metrics.py` MAY interpret `risk_free_rate` as a per-period rate matching the return frequency in `strategy_return`.
- `metrics.py` MAY preserve the current output schema by leaving `MetricReport` field names unchanged.

#### Explicit non-responsibilities

- `BacktestConfig` MUST NOT become the owner of risk-free-rate configuration in this change.
- `report.py`, `storage.py`, and `cli.py` MUST NOT recompute Sharpe by applying a separate risk-free adjustment locally.

#### Inputs / outputs / contracts

- Inputs:
  - per-period `strategy_return` series
  - `annualization_factor`
  - optional per-period `risk_free_rate`
- Output:
  - `MetricReport.sharpe_ratio`
- Contract rules:
  - the caller is responsible for converting any annual risk-free assumption into the matching per-period rate before calling `metrics.py`
  - omitting `risk_free_rate` preserves the previous raw-return behavior through the default `0.0`

#### Invariants

- Sharpe semantics have one authoritative implementation.
- Backward compatibility is preserved for callers that do not pass `risk_free_rate`.
