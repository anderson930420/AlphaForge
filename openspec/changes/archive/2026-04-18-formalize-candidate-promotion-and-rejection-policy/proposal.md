# Proposal: Formalize candidate promotion and rejection policy

## Summary

AlphaForge already produces validation and walk-forward evidence summaries, but the repo does not yet have a small, explicit policy layer that decides whether a searched candidate should be promoted, rejected, or left inconclusive.

This change adds a deterministic post-search decision policy that consumes the existing evidence summaries and emits explicit policy decisions with stable reasons.

## Scope

- Add a canonical candidate promotion/rejection policy for `validate-search` and `walk-forward`.
- Keep the policy rule set small, deterministic, and explainable.
- Preserve the current evidence summaries while making the policy decision a separate runtime output.
- Update serialization and CLI payloads so the decision is visible in validation and walk-forward outputs.

## Out of scope

- Genetic algorithms.
- Random search.
- New strategy families.
- Workflow engines or research databases.
- New metrics formulas or a broad scoring framework.
