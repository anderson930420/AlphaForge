# Design: <change-name>

## Canonical ownership mapping

- Map each ownership decision to the exact source files, schemas, and adapters that will implement it.

## Contract migration plan

- State how authoritative contracts will be represented and how downstream layers will derive from them.

## Duplicate logic removal plan

- List every duplicated validator, formula, naming rule, or schema projection that must be removed or downgraded to advisory behavior.

## Verification plan

- Define tests or checks that prove each rule has one authoritative owner.

## Temporary migration states

- If temporary duplication is unavoidable, state the temporary owner, advisory copies, and exact removal trigger.
