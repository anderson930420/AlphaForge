# Tasks

## 1. Spec and contract alignment

- [ ] 1.1 Update the market-data boundary proposal and spec so `data_loader.py` is the canonical owner of market-data acceptance.
- [ ] 1.2 Explicitly separate TWSE source normalization from canonical acceptance validation.
- [ ] 1.3 Identify downstream consumers that must treat loader-accepted data as authoritative only.

## 2. Code migration

- [ ] 2.1 Move any remaining market-data acceptance wording out of adapters, CLI, and downstream modules.
- [ ] 2.2 Remove or downgrade duplicate schema ownership claims in `config.py`, `twse_client.py`, and any downstream helpers.
- [ ] 2.3 Update docs and comments so `config.py` is clearly input-only and `data_loader.py` is clearly authoritative.

## 3. Verification

- [ ] 3.1 Add or update tests that prove loader acceptance, duplicate handling, missing-data handling, and column ordering are canonical.
- [ ] 3.2 Add or update tests that prove TWSE adapter output is only a candidate frame until the loader accepts it.
- [ ] 3.3 Add or update tests that prove downstream modules rely on accepted market data instead of re-normalizing schema shape.

## 4. Cleanup

- [ ] 4.1 Remove stale comments or docstrings that imply adapters or downstream modules own market-data acceptance.
- [ ] 4.2 Update any derived documentation or workflow notes so readers can find the loader contract as the source of truth.
