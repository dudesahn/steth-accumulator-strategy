# Finding Discovery Report

Scan id: `351c58eb-604e-4d06-91a4-9a0d6e65626b`

Discovery used the production-only `rank_input.jsonl` and `deep_review_input.jsonl` worklists. All 16 rows received full-file receipts from independent file-review workers. Excluded input was not used for discovery: `src/test/**`, mocks, `lib/**` except directly relied-on API semantics, build/cache/broadcast output, `.audit/**`, `x-ray/**`, scanner reports, and cached analysis.

## Candidates

1. `CS-351C58EB-001`: Lido withdrawal return data encodes a `uint256[]` request-id array but the normal claim path decodes a scalar `uint256`. Found independently by three workers.
2. `CS-351C58EB-002`: `stakeAsset=false` is enforced in `_deployFunds` but not in keeper-reachable `_harvestAndReport` or `_tend`.
3. `CS-351C58EB-003`: Donated loose stETH/wstETH can make `Strategy4626._stake` deposit more than a downstream ERC4626 vault's current `maxDeposit`, reverting maintenance flows.
4. `CS-351C58EB-004`: `script/Deploy4626.s.sol` deploys `Strategy4626` directly, logs an intended management address, but does not set pending management, keeper, emergency admin, fee recipient, performance fee, or profit unlock settings.
5. `CS-351C58EB-005`: `StrategyAprOracle` returns constant 4% APR and ignores strategy/debt delta. Kept as deferred pending production registration or allocator reachability evidence.

## Discovery Closure

`work_ledger.jsonl`, `raw_candidates.jsonl`, `dedupe_report.md`, `deduped_candidates.jsonl`, per-candidate discovery ledgers, and `repository_coverage_ledger.md` were written. Validation should preserve or suppress these instances; it should not broaden discovery beyond the production-only worklist.
