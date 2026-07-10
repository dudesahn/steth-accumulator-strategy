# Validation Summary

Scan id: `351c58eb-604e-4d06-91a4-9a0d6e65626b`

Validation consumed `deduped_candidates.jsonl`, the discovery worker outputs, the coverage ledger, targeted existing tests, a read-only ABI probe, and one disposable Foundry PoC under the scan bundle.

## Closure Table

| candidate id | instance key | root control | method | disposition | confidence | survives |
| --- | --- | --- | --- | --- | ---: | --- |
| `CS-351C58EB-001` | `queue-claim-data-shape:src/Strategy.sol:99` | `src/Strategy.sol:99`, `src/Strategy.sol:105` | static trace, existing fork tests, `cast` ABI probe | reportable | 0.74 | yes |
| `CS-351C58EB-002` | `stake-control:src/BaseLSTAccumulator.sol:152` | `src/BaseLSTAccumulator.sol:152`, `src/BaseLSTAccumulator.sol:166` | static trace and existing focused fork test | reportable | 0.82 | yes |
| `CS-351C58EB-003` | `erc4626-maxdeposit-donation-dos:src/Strategy4626.sol:41` | `src/Strategy4626.sol:41` | disposable Foundry PoC against copied target code plus static trace | reportable | 0.88 | yes |
| `CS-351C58EB-004` | `deployment-config:script/Deploy4626.s.sol:18` | `script/Deploy4626.s.sol:18-20` | static deployment trace and safe-pattern comparison | reportable | 0.80 | yes |
| `CS-351C58EB-005` | `oracle-static-apr:src/periphery/StrategyAprOracle.sol:28` | `src/periphery/StrategyAprOracle.sol:28-32` | static trace, bounded registration search, existing oracle test | deferred | 0.65 | uncertain |

## Commands Used

- `forge build` succeeded for production compilation.
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/WithdrawalQueue.t.sol -vv --fork-url https://ethereum.publicnode.com` passed 7/7.
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-test test_harvestStakesBypassesStakeAssetFlag -vv --fork-url https://ethereum.publicnode.com` passed 1/1.
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/Oracle.t.sol -vv --fork-url https://ethereum.publicnode.com` passed 1/1.
- `cast abi-encode "f(uint256[])" "[123]"` produced dynamic-array bytes beginning with the offset word `0x20`; `cast decode-abi "f()(uint256)" ...` decoded the same bytes as `32`.
- In the disposable validation copy, `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/MaxDepositDonationPoC.t.sol -vv --fork-url https://ethereum.publicnode.com` passed 1/1.

Foundry emitted a non-material warning about writing signature cache outside the workspace during compile/build activity; the compile and targeted tests succeeded.
