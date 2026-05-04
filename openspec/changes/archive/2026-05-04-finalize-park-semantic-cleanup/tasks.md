# Tasks: Finalize Park Semantic Cleanup

- [x] Update the market-data boundary delta so duplicate datetimes fail instead of being collapsed.
- [x] Update the execution-semantics delta so trade logs are described only with return-based fields and no `net_pnl` wording.
- [x] Expand the custom-signal boundary delta so the external `signal.csv` contract and execution mapping are explicit.
- [x] Add architecture-boundary wording that positions AlphaForge as a validation engine rather than the alpha-generation platform.
- [x] Run OpenSpec validation on the cleanup change.
- [x] Confirm no runtime code or tests were changed.
