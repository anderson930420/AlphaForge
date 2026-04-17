# Tasks

## 1. Spec alignment

- [x] 1.1 Add an OpenSpec delta for candidate validation and evidence contracts.
- [x] 1.2 Document candidate evidence, degradation semantics, walk-forward aggregate evidence, and verdict vocabulary.

## 2. Implementation

- [x] 2.1 Add runtime evidence summary dataclasses to `src/alphaforge/schemas.py`.
- [x] 2.2 Add helper functions for verdict derivation, degradation summaries, and evidence assembly.
- [x] 2.3 Thread candidate evidence through validation and walk-forward runner outputs.
- [x] 2.4 Update storage serializers and CLI output to include the new evidence summaries.

## 3. Verification

- [x] 3.1 Add tests for stable validation evidence fields.
- [x] 3.2 Add tests for stable walk-forward aggregate evidence fields.
- [x] 3.3 Add tests for degradation field behavior.
- [x] 3.4 Add tests for verdict/status behavior.
- [x] 3.5 Add tests for CLI output consistency for `validate-search` and `walk-forward`.

## 4. Cleanup

- [x] 4.1 Update README only if the new evidence fields materially change user-facing output guarantees.
- [x] 4.2 Log the implementation and verification steps back to project memory.
