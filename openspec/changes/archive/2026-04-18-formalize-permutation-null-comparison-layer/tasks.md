# Tasks

## 1. Spec alignment

- [x] 1.1 Add an OpenSpec delta for the permutation/null-comparison diagnostic.
- [x] 1.2 Document what is permuted, what stays fixed, the target metric, and the summary artifact contract.

## 2. Implementation

- [x] 2.1 Add a minimal permutation module that evaluates the fixed MA candidate on real and permuted data.
- [x] 2.2 Add runtime summary and receipt contracts for the permutation diagnostic.
- [x] 2.3 Add storage serialization for the permutation summary and score-list artifacts.
- [x] 2.4 Add a CLI command that dispatches the diagnostic and prints the canonical payload.

## 3. Verification

- [x] 3.1 Add tests for deterministic permutation behavior with a fixed seed.
- [x] 3.2 Add tests for the empirical comparison statistic and summary fields.
- [x] 3.3 Add tests for CLI and storage output consistency.

## 4. Cleanup

- [x] 4.1 Update canonical specs and README only if user-facing guarantees changed.
- [x] 4.2 Log the implementation and verification steps back to project memory.
