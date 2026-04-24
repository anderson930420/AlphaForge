# Proposal: Harden Bar Count and TWSE SSL Fallback

## Why

AlphaForge still has a few contract and safety gaps that can silently distort scoring or leak insecure network behavior into normal execution. In particular, `MetricReport.bar_count` must not default to a non-positive value, scoring must fail fast on malformed metrics, the TWSE SSL retry path must be explicitly logged and warning-scoped, and walk-forward mean Sharpe output needs an explicit descriptive-only contract note.

## What Changes

- Make `MetricReport.bar_count` a required positive runtime contract.
- Make `scoring.py` reject invalid `bar_count` values instead of falling back to cumulative turnover semantics.
- Keep `compute_metrics()` producing valid positive `bar_count` values from real equity curves and reject empty equity curves.
- Harden the TWSE SSL fallback so the warning is logged and `InsecureRequestWarning` is suppressed only inside the insecure retry block.
- Clarify that walk-forward `mean_test_sharpe_ratio` is descriptive fold-average output only and not a decision-grade promote/reject statistic.

## Impact

- Invalid metric objects fail earlier and cannot silently contaminate scoring.
- TWSE fallback behavior becomes auditable without changing the normal verified request path.
- Walk-forward policy semantics remain unchanged, but the evidence contract is clearer about which Sharpe values are decision-grade.
