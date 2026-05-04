# Proposal: Finalize Park Semantic Cleanup

## Change Name

finalize-park-semantic-cleanup

## Why

AlphaForge is already parked as a validation engine, but a few canonical contracts still carry stale or contradictory wording. The final park-readiness pass should make the accepted semantics unambiguous before the repo is treated as stable v0.1 documentation.

## What Changes

- Make the canonical market-data policy fail on duplicate datetimes instead of silently collapsing them.
- Clean the canonical execution semantics wording so trade logs are described in return-based fields only, without dollar-PnL labels such as `net_pnl`.
- Expand the canonical custom-signal contract so it explicitly defines the external `signal.csv` schema, execution mapping, date alignment rules, and SignalForge import boundary.
- Tighten the AlphaForge boundary wording so the project is clearly positioned as a validation engine, not an alpha-generation platform.

## Capabilities

### New Capability

- `finalize-park-semantic-cleanup`

### Modified Capabilities

- `market-data-schema-and-adapter-boundary`
- `execution-semantics-contract`
- `custom-signal-interface`
- `alphaforge-architecture-boundary-map`

## Impact

This is a spec-only cleanup change. It should not introduce runtime behavior changes yet, but it will remove ambiguity before the runtime policy cleanup is implemented.

