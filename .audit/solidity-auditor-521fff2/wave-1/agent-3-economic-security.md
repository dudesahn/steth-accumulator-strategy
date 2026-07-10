# Agent 3 - Economic Security

Scope: stETH Accumulator Strategy at commit `521fff28ad978a37115be8995a1d631611fa1d3d`.

Read basis: `agent-3-bundle.md` for in-scope source and lane rules. X-ray artifacts were used only for orientation. Out-of-scope proof checks used `src/interfaces/`, `src/test/`, `src/test/mocks/`, and `lib/tokenized-strategy/src/TokenizedStrategy.sol`.

## Tool Markers

[Feynman: BaseLSTAccumulator] This base strategy takes WETH from users, usually turns it into stETH-side exposure, reports the strategy's asset value, and only lets ordinary withdrawals use loose WETH already sitting in the strategy. If redemptions are pending from the Lido queue, it refuses to report.

[Feynman: BaseLSTAccumulator._harvestAndReport] This report step first refuses to run while a Lido withdrawal is outstanding, then sells rewards if any, then turns loose WETH back into stETH exposure, and finally tells TokenizedStrategy how much WETH-equivalent value the strategy has.

[Inversion: BaseLSTAccumulator._harvestAndReport] 1. Leave `pendingRedemptions` nonzero so reports cannot update accounting. 2. Claim queue ETH but run a report before users withdraw so loose WETH is restaked. 3. Donate or manipulate LST-side balances before report so the next total-assets update records a value shift.

[Feynman: BaseLSTAccumulator.initiateLSTWithdrawal] Management asks the strategy to move some stETH-side value into Lido's withdrawal queue, and the strategy records that amount as pending before returning the data operators need for a later claim.

[Socratic: bundle:265 - why store `_amount` before knowing claim output?] The code assumes the queued stETH amount and the eventual ETH claim amount will be close enough that a later claim can decrement the pending counter; if the claim path cannot decode the request correctly, this pending value becomes a report blocker.

[Feynman: Strategy._initiateLSTWithdrawal] The stETH strategy approves the Lido queue, puts the requested stETH amount into a one-item list, asks Lido for withdrawal request ids, and returns the encoded list of ids.

[Socratic: bundle:390 - why return the full encoded request-id array?] The code appears to preserve Lido's native return shape, but the matching claim helper reads a different shape.

[Feynman: Strategy._claimLSTWithdrawal] The claim helper reads one request id from the provided bytes, asks Lido to claim that request, measures how much ETH arrived, and wraps all ETH held by the strategy into WETH.

[Socratic: bundle:396 - why decode one integer from claim data that initiation returns as an array?] The implicit belief is that claim data is already a single request id, but the initiation function returns `abi.encode(uint256[] requestIds)`.

[Inversion: Strategy._claimLSTWithdrawal] 1. Pass the raw bytes returned by `initiateLSTWithdrawal` and make the helper claim request id `32` instead of the actual id. 2. Pass a stale or already-claimed request id so the queue reverts and pending stays nonzero. 3. Claim through the emergency batch path while leaving `pendingRedemptions` nonzero to keep reports blocked.

[Feynman: Strategy._stake] The strategy unwraps WETH into ETH, checks whether Curve gives more stETH than direct Lido staking, and either swaps through Curve with a one-for-one minimum or stakes directly with Lido.

[Inversion: Strategy._stake] 1. Make Curve return just over one-for-one so the actual stETH received exceeds the amount that upstream capacity checks assumed. 2. Make Curve quote over one-for-one but execute at exactly the minimum so expected surplus disappears. 3. Keep Lido staking paused so deposits are closed through `_depositLimit`.

[Feynman: Strategy4626.availableDepositLimit] The 4626 extension asks the downstream wstETH vault how much wstETH it can accept, converts that amount into stETH terms, and exposes the result as this strategy's WETH deposit capacity.

[Socratic: bundle:487 - why is downstream capacity converted before the strategy knows actual Curve output?] The code assumes one WETH deposit becomes no more than one WETH-equivalent of stETH/wstETH, but the Curve branch is selected specifically when it returns more stETH than the input amount.

[Feynman: Strategy4626._stake] The extension first gets stETH through the base staking route, wraps every stETH wei into wstETH, and deposits every resulting wstETH wei into the downstream vault.

[Inversion: Strategy4626._stake] 1. Use a downstream vault with a finite `maxDeposit` and a Curve premium so the actual wstETH deposit exceeds the advertised capacity. 2. Use a vault whose conversion views overstate redeemable assets so reports value more than can be unwound. 3. Set the vault cap to zero between the user's max-deposit read and the final vault deposit so the transaction reverts.

[Feynman: StrategyAprOracle.aprAfterDebtChange] The APR oracle ignores the strategy address and the requested debt change, and always answers that the strategy earns four percent per year.

[Inversion: StrategyAprOracle.aprAfterDebtChange] 1. Query with a huge positive debt change and still receive the same APR. 2. Query a paused or illiquid strategy and still receive the same APR. 3. Query two different strategies and receive identical APRs even if their external vault economics differ.

FINDING | contract: Strategy | function: claimLSTWithdrawal | bug_class: queue-claim-data-mismatch | group_key: Strategy | claimLSTWithdrawal | queue-claim-data-mismatch
path: management -> `initiateLSTWithdrawal(amount)` -> `pendingRedemptions += amount` and `_initiateLSTWithdrawal` returns `abi.encode(uint256[] requestIds)` -> keeper or management passes that returned data to `claimLSTWithdrawal` -> `_claimLSTWithdrawal` decodes the first ABI word as a single `uint256` request id -> Lido claim targets id `32` instead of the created request id -> claim reverts or claims the wrong id, `pendingRedemptions` is not reduced, and `_harvestAndReport` remains blocked by `pendingRedemptions != 0`.
proof: `IQueue.requestWithdrawals` returns `uint256[]`; bundle lines 382-390 build a one-item array and return `abi.encode(requestIds)`, while bundle lines 395-399 decode `_claimData` as `(uint256)` and call `claimWithdrawal(_requestId)`. For concrete bytes, `cast abi-encode "f(uint256[])" "[1]"` produced `0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001`; decoding those same bytes as `f()(uint256)` returned `32`, while decoding as `f()(uint256[])` returned `[1]`. The current tests avoid this failing handoff by decoding `returnData` and calling `claimLSTWithdrawal(abi.encode(requestIds[0]))` at `src/test/WithdrawalQueue.t.sol:72-80` and `src/test/WithdrawalQueue.t.sol:106-117`. With any positive pending amount, bundle line 150 makes `report()` revert with `Pending redemptions` until a correctly encoded single id is supplied, emergency batch claim zeroes pending, or management clears pending manually.
description: The documented claim-data handoff is internally inconsistent, so the normal queue claim path can fail to clear redemptions and freeze report-cycle accounting.
fix: Make the two helpers agree on one data shape: either return `abi.encode(requestIds[0])` from `_initiateLSTWithdrawal` for single-request queues, or decode `(uint256[] memory requestIds)` in `_claimLSTWithdrawal` and claim the intended element(s); add a regression test that passes `returnData` from initiation directly into `claimLSTWithdrawal`.

FINDING | contract: Strategy4626 | function: availableDepositLimit | bug_class: max-deposit-overstatement | group_key: Strategy4626 | availableDepositLimit | max-deposit-overstatement
path: user or integrator -> `maxDeposit(receiver)` / `_maxDeposit` -> `Strategy4626.availableDepositLimit` returns `_stETHValue(vault.maxDeposit(address(this)))` -> user deposits that advertised WETH amount -> `Strategy._stake` chooses Curve because `get_dy(ETH, stETH, amount) > amount` -> actual stETH received is greater than the checked input amount -> all resulting wstETH is deposited into the downstream vault -> vault deposit reverts because the actual wstETH amount exceeds the vault's finite `maxDeposit`.
proof: Bundle lines 483-489 cap deposits with `vault.maxDeposit(address(this))` converted from wstETH to stETH terms before staking. Bundle lines 349-355 intentionally route through Curve only when `get_dy` is greater than `_amount`, and bundle lines 457-469 then wrap all stETH and call `vault.deposit(wstETHBalance, address(this))` without rechecking the downstream cap. Concrete values: if `vault.maxDeposit(strategy) = 100e18` wstETH and `1 wstETH = 1.05 stETH`, `availableDepositLimit` advertises `105e18` WETH-equivalent. If Curve returns `106e18` stETH for `105e18` ETH, the strategy wraps about `100.952e18` wstETH and tries to deposit it into a vault that said it could accept only `100e18`; the user-supplied `deposit(maxDeposit(receiver), receiver)` passes TokenizedStrategy's precheck but reverts at the downstream vault. The targeted `Strategy4626Test` suite passed on a mainnet fork, but it uses the live configured vault path and does not cover a finite vault cap plus Curve-premium fill.
description: The ERC4626 extension can advertise a maximum deposit that is no longer executable after the favorable Curve route produces extra stETH.
fix: Leave headroom when translating downstream vault capacity, or cap the actual wstETH deposited to `vault.maxDeposit(address(this))` after staking and leave/swap the surplus separately.

LEAD | contract: BaseLSTAccumulator | function: estimatedTotalAssets | bug_class: lst-peg-accounting | group_key: BaseLSTAccumulator | estimatedTotalAssets | lst-peg-accounting
code_smells: `estimatedTotalAssets` prices direct stETH and Strategy4626's wstETH/vault assets at nominal stETH value with only `reportBuffer`, TokenizedStrategy records donated or newly visible balances on report, factory-created Strategy4626 instances set `profitMaxUnlockTime` to zero, and ordinary exits are limited to idle WETH.
description: A discounted-stETH donation/report/withdraw value-transfer may be possible if an attacker can own a very large share fraction and find or induce idle WETH liquidity, but this lane did not prove the missing conditions because normal deposits stake WETH immediately and untrusted users cannot force the management unwind that creates idle exit liquidity.

LEAD | contract: Strategy4626 | function: valueOfWstETH | bug_class: external-vault-nav-overstatement | group_key: Strategy4626 | valueOfWstETH | external-vault-nav-overstatement
code_smells: `valueOfWstETH` reports `vault.convertToAssets(vault.balanceOf(address(this)))`, while unwind uses `previewWithdraw`, `maxRedeem`, and `redeem`; the constructor only checks that the vault asset is wstETH, not that conversion views equal immediately redeemable value.
description: A downstream vault with illiquidity, withdrawal limits, fees not reflected in `convertToAssets`, or malicious conversion semantics could make reports value more wstETH than the strategy can actually free, but no concrete in-repo vault with those economics was proven in this pass.

LEAD | contract: Strategy4626Factory | function: newStrategy4626 | bug_class: external-vault-reentrancy | group_key: Strategy4626Factory | newStrategy4626 | external-vault-reentrancy
code_smells: `newStrategy4626` checks `deployments[_vault]`, then calls user-controlled `_vault.symbol()` and deploys `Strategy4626`, whose constructor calls `_vault.asset()`, before writing `deployments[_vault] = address(newStrategy)`.
description: A malicious vault can likely reenter during `symbol()` or `asset()` and create multiple strategies for the same vault before the registry slot is written, but this lane did not prove a user-fund impact because the vault is attacker-supplied and deposits are still closed until strategy management acts.

LEAD | contract: StrategyAprOracle | function: aprAfterDebtChange | bug_class: static-apr-mispricing | group_key: StrategyAprOracle | aprAfterDebtChange | static-apr-mispricing
code_smells: The oracle returns `4e16` for every `_strategy` and every positive or negative `_delta`; `src/test/Oracle.t.sol` only checks the answer is nonzero and below 100%, with the debt-change monotonicity checks left as TODO comments.
description: If this oracle is wired into a debt allocator, it can route capital based on a fixed APR that ignores stETH peg conditions, downstream vault yield/capacity, report buffers, and debt size, but no in-repo consumer was found to turn the stale APR into an immediate value-moving exploit.

## Verification Notes

- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-contract WithdrawalQueueTest -vv --fork-url https://ethereum.publicnode.com` passed: 7 tests.
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-contract Strategy4626Test -vv --fork-url https://ethereum.publicnode.com` passed: 5 tests.
- ABI sanity check: the encoded `uint256[]` value `[1]` decodes as scalar `uint256(32)` and as array `[1]`, matching the queue claim mismatch above.
