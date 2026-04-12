# Tasks

## 1. Spec and contract alignment

- [ ] 1.1 Update proposal and boundary specs to name the canonical owner for each affected rule.
- [ ] 1.2 Identify every downstream adapter or advisory validator that must derive from the canonical owner.

## 2. Code migration

- [ ] 2.1 Move authoritative logic into the canonical owner.
- [ ] 2.2 Remove or downgrade duplicate implementations in non-owning modules.
- [ ] 2.3 Update CLI, storage, report, and orchestration layers to consume derived contracts instead of redefining them.

## 3. Verification

- [ ] 3.1 Add or update tests that prove business rules and schemas are not multiply owned.
- [ ] 3.2 Verify execution semantics are explicit in the owning contract rather than implicit in orchestration flow.

## 4. Cleanup

- [ ] 4.1 Delete stale compatibility code once migration checks pass.
- [ ] 4.2 Update documentation and worklog entries for the new ownership boundary.
