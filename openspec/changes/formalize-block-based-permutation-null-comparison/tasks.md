# Tasks

## 1. Spec alignment

- [x] 1.1 Add an OpenSpec delta for block-based permutation/null-comparison semantics.
- [x] 1.2 Document block formation, block-order shuffling, the new `block_size` parameter, and summary fields.

## 2. Implementation

- [x] 2.1 Replace the current whole-row shuffle with block-order shuffling in the permutation module.
- [x] 2.2 Add `block_size` and permutation mode fields to the runtime summary contract.
- [x] 2.3 Add serialization updates for the new summary fields while keeping existing artifact names.
- [x] 2.4 Update CLI parsing to require block size for permutation runs.

## 3. Verification

- [x] 3.1 Add tests for deterministic block permutation behavior.
- [x] 3.2 Add tests for invalid block-size handling.
- [x] 3.3 Add tests for summary-field stability, serialization types, and CLI/storage output consistency.

## 4. Cleanup

- [x] 4.1 Update README only if user-facing CLI/output guarantees changed.
- [x] 4.2 Log implementation and verification steps back to project memory.
