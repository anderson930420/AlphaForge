# <capability-name> Specification

## Purpose

- State the exact capability boundary this spec governs.

## Canonical owner

- Name the single module, package, or artifact that is authoritative for this boundary.

## Allowed responsibilities

- List only the responsibilities that belong to the canonical owner.

## Explicit non-responsibilities

- List responsibilities that must not be implemented or redefined here.

## Inputs / outputs / contracts

- Define the accepted inputs, produced outputs, and contract surfaces that this owner controls.

## Invariants

- List the rules that must remain true across all executions.

## Cross-module dependencies

- Name upstream inputs and downstream consumers, and identify which contracts are authoritative versus derived.

## Failure modes if this boundary is violated

- State the concrete failure patterns that occur when another module also owns this logic.

## Migration notes from current implementation

- State what currently exists, what must move, and what must be deleted or downgraded to an adapter.

## Open questions / deferred decisions

- List only unresolved decisions that are intentionally left open after defining the boundary.
