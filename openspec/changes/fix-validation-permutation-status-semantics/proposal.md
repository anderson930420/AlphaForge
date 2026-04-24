# Proposal: Fix Validation Permutation Status Semantics

## Summary

Validation permutation evidence currently uses a status value that conflates diagnostic completion with threshold failure. A successfully completed diagnostic that misses the p-value threshold should be reported as completed-but-failed, not as an execution failure.

## Scope

- Separate permutation execution status from policy verdict semantics in validation outputs.
- Introduce explicit validation permutation statuses for skipped, completed_passed, completed_failed, and error.
- Preserve research policy rejection behavior when p-value enforcement fails.

## Non-Goals

- No changes to permutation algorithms.
- No changes to candidate selection, scoring, or research policy thresholds.
- No new strategy families or orchestration redesign.
