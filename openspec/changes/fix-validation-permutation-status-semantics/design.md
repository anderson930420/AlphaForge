# Design: Fix Validation Permutation Status Semantics

## Overview

The validation workflow already produces permutation evidence and passes it into research policy. This change only corrects the meaning of the validation-side status field so it reflects execution outcome rather than policy outcome.

## Status Model

- `skipped`: permutation diagnostics were not requested or were explicitly opted out.
- `completed_passed`: permutation diagnostics ran successfully and met the configured p-value threshold.
- `completed_failed`: permutation diagnostics ran successfully but the empirical p-value exceeded the configured threshold.
- `error`: the permutation diagnostic could not produce usable evidence, including runtime failures or missing summary data.

## Policy Boundary

- `research_policy.py` continues to own the rejection decision.
- A `completed_failed` diagnostic still contributes real evidence and still causes policy rejection under the default threshold.
- A permutation execution `error` remains distinct from a threshold failure so reports can distinguish broken diagnostics from failed evidence.

## Compatibility

- The change is limited to validation evidence status semantics and test coverage.
- Artifact persistence and permutation execution logic remain unchanged.
