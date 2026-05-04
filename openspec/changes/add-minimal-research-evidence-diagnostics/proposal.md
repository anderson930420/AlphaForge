# Proposal: Add Minimal Research Evidence Diagnostics

## Change Name

add-minimal-research-evidence-diagnostics

## Why

AlphaForge is close to park-ready, but it still needs minimal research evidence diagnostics before v0.1 can be treated as stable. The remaining A5/A6 gap is small and well-bounded: cost sensitivity and bootstrap evidence. The goal is not to build a full transaction-cost simulator or advanced multiple-testing framework, but to make sure AlphaForge does not overstate evidence quality.

## What Changes

- Add cost-sensitivity diagnostics that rerun the selected research candidate under low, base, and high cost assumptions.
- Add bootstrap evidence diagnostics that compute confidence intervals for return evidence with recorded sample count and seed.
- Surface both diagnostics in research-validation artifacts, report view models, and storage-owned summaries.
- Keep the scope deliberately minimal and exclude PBO, DSR, White Reality Check, Hansen SPA, full TCA, broker execution, LOB simulation, and other advanced diagnostics.

## Capabilities

### New Capability

- `add-minimal-research-evidence-diagnostics`

### Modified Capabilities

- `research-validation-protocol`
- `candidate-validation-and-evidence-contract`
- `storage-artifact-ownership`
- `report-view-model-contract`
- `alphaforge-architecture-boundary-map`

## Impact

This is a spec-only change. It defines the minimal diagnostics contract needed before park readiness, but it does not yet change runtime code or tests.

