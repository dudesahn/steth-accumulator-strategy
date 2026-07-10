# Discovery Dedupe Report

Scan id: `351c58eb-604e-4d06-91a4-9a0d6e65626b`

## Canonical Candidates

- `CS-351C58EB-001` absorbs `CS-FD-351C-S02-001`, `CS-351C58EB-IFACE-001`, and `CS-351C58EB-S05-001`. These are the same Lido withdrawal request-data ABI mismatch: `requestWithdrawals` returns `uint256[]`, `Strategy._initiateLSTWithdrawal` returns `abi.encode(requestIds)`, and `Strategy._claimLSTWithdrawal` decodes `_claimData` as scalar `uint256`.
- `CS-351C58EB-002` preserves `FD-351C58EB-BASE-001`. No duplicate was found; it is the stake-control bypass around `stakeAsset=false` in report/tend.
- `CS-351C58EB-003` preserves `CS-351c58eb-S03-001`. No duplicate was found; it is the ERC4626 `maxDeposit` donation/loose-balance griefing path.
- `CS-351C58EB-004` preserves `CS-351c58eb-S06-001`. No duplicate was found; it is the standalone `Deploy4626` deployment-configuration path.
- `CS-351C58EB-005` preserves `CS-351C58EB-S05-002` as a deferred validation row. It is not merged into any strategy accounting issue because the root proof gap is production APR-oracle registration.

## Dedupe Notes

The Lido claim-data issue appeared independently from three shards and was merged because all three name the same source, broken control, sink, and report-blocking effect. The base, 4626, deployment, and APR-oracle rows are distinct proof tuples and remain separate for validation.
