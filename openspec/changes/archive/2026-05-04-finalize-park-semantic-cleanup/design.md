# Design: Finalize Park Semantic Cleanup

## Context

AlphaForge has completed the major validation-engine work and is ready for park mode, but several canonical spec phrases still disagree with the current runtime intent:

- duplicate OHLCV datetimes are still described as collapseable in the market-data boundary
- old PnL-shaped wording still appears alongside return-based trade semantics
- the custom-signal boundary is still narrower than the implemented handoff needs
- the repository boundary is not yet explicit enough about AlphaForge being a validation layer

## Goals

- Make the canonical contracts internally consistent before v0.1 parking.
- Keep the cleanup narrow and limited to boundary wording and policy direction.
- Avoid introducing new diagnostics, signal features, or alpha-generation scope.

## Non-Goals

- No runtime code changes yet.
- No tests yet.
- No cost-sensitivity diagnostics.
- No bootstrap / multiple-testing diagnostics.
- No new signal-generation features.
- No SignalForge integration changes.
- No live trading, broker simulation, portfolio optimization, or ML pipeline work.

## Decisions

1. The market-data boundary should fail duplicate datetimes instead of collapsing them.
2. The execution-semantics boundary should use the current return-based trade contract as the only public wording.
3. The custom-signal boundary should explicitly describe the external file contract and the signal_binary-to-target_position mapping.
4. The architecture boundary should state that AlphaForge is a parked validation engine, not the alpha-generation owner.

## Risks and Trade-offs

- The duplicate-datetime policy change will require a follow-up runtime change later, so the spec should be precise enough to avoid partial implementation.
- Tightening the custom-signal contract may surface a few stale assumptions in future docs or examples.
- Boundary cleanup should remain narrow so it does not become a catch-all documentation rewrite.

## Migration Strategy

- First update the canonical spec deltas.
- Then implement runtime policy changes in a separate change after the cleanup spec is archived.
- Keep the cleanup isolated from cost-sensitivity, bootstrap, or other research-diagnostic work.

## Open Questions

- Whether any README wording needs an immediate follow-up is deferred unless the spec change exposes a direct inconsistency.

