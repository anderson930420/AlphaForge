# Design: Harden Bar Count and TWSE SSL Fallback

## Overview

This change is a small hardening pass on existing runtime contracts. It does not redesign metrics, scoring, or walk-forward aggregation. It tightens validation and clarifies semantics where the current code can silently drift.

## Metric Contract

- `MetricReport.bar_count` is required and must be a positive integer.
- `compute_metrics()` is responsible for constructing valid metric reports from equity curves.
- `scoring.py` must not normalize invalid bar counts away.

## TWSE Fallback

- The normal TWSE request path continues to use SSL verification.
- Only `requests.exceptions.SSLError` triggers the fallback retry.
- The fallback emits a warning log and suppresses `InsecureRequestWarning` locally, only for the insecure retry request.

## Walk-Forward Sharpe

- `mean_test_sharpe_ratio` remains in aggregate walk-forward output as descriptive fold-average data.
- Decision-grade walk-forward promotion and rejection must rely on `pooled_test_sharpe_ratio` when that statistic is available.
- This change documents that interpretation without changing the aggregation algorithm.
