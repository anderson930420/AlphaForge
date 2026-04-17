# Tasks

## 1. Spec alignment

- [x] 1.1 Add an OpenSpec delta for candidate promotion and rejection policy.
- [x] 1.2 Document policy inputs, outputs, scope, and decision semantics.

## 2. Implementation

- [x] 2.1 Add a minimal policy module that evaluates validation and walk-forward evidence.
- [x] 2.2 Add a runtime policy decision contract to `src/alphaforge/schemas.py`.
- [x] 2.3 Thread policy decisions through validation and walk-forward runner outputs.
- [x] 2.4 Update storage serializers and CLI output to include policy decisions.

## 3. Verification

- [x] 3.1 Add tests for validated, rejected, and inconclusive validation decisions.
- [x] 3.2 Add tests for validated, rejected, and inconclusive walk-forward decisions.
- [x] 3.3 Add tests for decision reasons.
- [x] 3.4 Add tests for CLI and storage output consistency.

## 4. Cleanup

- [x] 4.1 Update README only if the new decision outputs change user-facing guarantees.
- [x] 4.2 Log the implementation and verification steps back to project memory.
