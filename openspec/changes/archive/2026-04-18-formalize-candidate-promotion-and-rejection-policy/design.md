# Design: Formalize candidate promotion and rejection policy

## Decision model

The policy is a shared rule set applied in two places:

- `validate-search` uses candidate evidence assembled from the train/test split.
- `walk-forward` uses fold-level candidate evidence and the aggregate walk-forward evidence summary.

The policy emits a small decision object with:

- policy name
- policy scope
- final verdict
- stable decision reasons

## Boundary

- Search selects and ranks candidates.
- Validation builds evidence.
- The policy evaluates evidence and returns a decision.
- Storage serializes the decision.
- CLI prints the serialized result only.
- Report code must not invent decisions.

## Expected behavior

- `validated` is reserved for evidence that is complete and clearly passes the current policy.
- `rejected` is reserved for evidence that is complete and clearly fails the current policy.
- `inconclusive` is used whenever evidence is incomplete, partially available, or mixed.

## Decision reasons

Decision reasons are short stable codes. They are meant to explain why a decision was made without becoming a separate rule language.
