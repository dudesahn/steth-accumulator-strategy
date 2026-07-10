# Agent 12 - Flow Gap Hunter

Scope: stETH accumulator strategy at commit 521fff28ad978a37115be8995a1d631611fa1d3d.

## Working markers

[Feynman: BaseLSTAccumulator] This contract is the shared shell for a strategy that accepts WETH, turns WETH into a liquid staking position, reports that position as WETH-equivalent value, and exposes role-controlled ways to move value back toward WETH. The fuzzy spot is that "value" is not one place: it can be idle WETH, held LST, wrapped/vaulted LST, or a pending withdrawal claim that has left the token balance but has not returned as WETH.

[Feynman: BaseLSTAccumulator._depositLimit] This function answers "how much more WETH can enter before the management cap is reached?" by subtracting the strategy's currently visible WETH-equivalent balance from `depositLimit`. If any real strategy value is temporarily invisible to `estimatedTotalAssets()`, this answer becomes too large.

[Inversion: BaseLSTAccumulator._depositLimit] 1. Move 100 stETH into the Lido queue so the strategy still owns an economic claim but no longer holds stETH. 2. Query `availableDepositLimit()` before the queue claim returns WETH. 3. Deposit the newly opened room, then claim the queued withdrawal so total exposure exceeds the original cap.

[Feynman: BaseLSTAccumulator._harvestAndReport] This report path refuses to run while Lido withdrawals are pending, optionally claims rewards, tries to turn spare WETH into the LST position, and then returns the strategy's visible value. The important gap is that it calls `_stake()` even when the amount chosen for staking is zero.

[Socratic: src/BaseLSTAccumulator.sol:152 - why call _stake when the chosen amount may be zero?] The call is meant to be harmless for the base stETH strategy, but the 4626 override also sweeps loose stETH/wstETH into the downstream vault, so zero WETH does not mean zero external effect.

[Feynman: BaseLSTAccumulator.initiateLSTWithdrawal] Management asks to turn held LST value into a Lido queue claim. The strategy records the requested amount as pending, then sends stETH to the queue and returns bytes that the caller must later interpret.

[Feynman: BaseLSTAccumulator.claimLSTWithdrawal] A keeper supplies bytes identifying a withdrawal request. The strategy asks the Lido queue to pay ETH for that request, wraps all ETH it holds into WETH, and lowers `pendingRedemptions` by the ETH newly received.

[Inversion: BaseLSTAccumulator.claimLSTWithdrawal] 1. Feed the exact bytes returned by `initiateLSTWithdrawal()` instead of a freshly encoded single id. 2. Claim a lower-than-requested Lido redemption and leave nonzero pending dust. 3. Claim through the emergency batch path with `_zeroRedemptions` set inconsistently with the actual batch.

[Feynman: Strategy._stake] This function turns WETH into ETH, then either swaps ETH for stETH through Curve when Curve promises more than direct staking, or sends ETH to Lido for stETH. The path assumes the chosen external route either gives at least the original amount of stETH or reverts.

[Feynman: Strategy._swapLSTToAsset] This function approves stETH to Curve, swaps stETH into ETH, then wraps every ETH wei sitting on the strategy into WETH. The raw ETH balance is swept globally, not just the ETH from this swap.

[Feynman: Strategy._initiateLSTWithdrawal] This function approves the Lido queue, builds a one-element amount array, asks the queue to create withdrawal request ids for this strategy, and returns the encoded array of request ids.

[Socratic: src/Strategy.sol:99 - why return abi.encode(requestIds) while claim decodes a uint256?] The request side preserves Lido's array shape, while the single-claim side expects a single request id; callers must know to decode the array and re-encode one element.

[Feynman: Strategy._claimLSTWithdrawal] This function treats the supplied bytes as one request id, claims that request from the Lido queue, measures how much ETH arrived, and wraps ETH into WETH.

[Feynman: Strategy4626] This extension keeps the strategy's stETH exposure inside wstETH and a downstream ERC4626 vault. The fuzzy spot is that vault capacity is checked in `availableDepositLimit()`, but the actual sweep into the vault happens later inside `_stake()`.

[Feynman: Strategy4626._stake] This function first performs the normal WETH-to-stETH stake, then wraps every stETH balance into wstETH, then deposits every wstETH balance into the downstream vault. Even if it receives `_amount == 0`, it still sweeps existing stETH/wstETH balances.

[Inversion: Strategy4626._stake] 1. Transfer 1 wei of wstETH directly to the strategy while the downstream vault has `maxDeposit(strategy) == 0`. 2. Trigger `report()` when no WETH is idle, forcing `_stake(0)` to try `vault.deposit(1, strategy)`. 3. Donate enough loose wstETH to push `wstETHBalance` above a nonzero `maxDeposit`, making an otherwise allowed report/deposit revert at the vault boundary.

[Feynman: Strategy4626.availableDepositLimit] This function starts with the strategy's own cap and then lowers it to match how much wstETH the downstream vault says it can accept. It protects planned WETH deposits, but it does not protect forced loose wstETH already sitting on the strategy.

[Feynman: Strategy4626._freeStETH] This function tries to make enough stETH available by using held stETH first, redeeming vault shares for wstETH if needed, and unwrapping the loose wstETH balance. The fuzzy spot is that it unwraps the whole loose wstETH balance, not only the amount needed for the requested operation.

[Inversion: Strategy4626._freeStETH] 1. Leave a large loose wstETH balance through `manualRedeem()`, then request a tiny stETH amount. 2. Make `vault.maxRedeem(strategy) == 0` so the function cannot free the requested amount but still continues with whatever is loose. 3. Use a small swap request to convert the entire loose wrapped balance into direct stETH while only swapping the requested amount to WETH.

[Feynman: Strategy4626Factory.newStrategy4626] Anyone can ask the factory to create one strategy for a chosen vault. The function checks the registry, calls the vault for its symbol and asset during construction, configures the new strategy, emits an event, and only then records the vault-to-strategy mapping.

[Inversion: Strategy4626Factory.newStrategy4626] 1. Use a vault whose `symbol()` reenters `newStrategy4626(vault)` before the mapping is written. 2. Use a vault whose `asset()` reenters during the `Strategy4626` constructor. 3. Emit multiple strategy creation events for the same vault, then let the last returning call overwrite the registry entry.

## Structured output

FINDING | contract: Strategy4626 | function: _stake | bug_class: forced-wsteth-report-dos | group_key: Strategy4626 | _stake | forced-wsteth-report-dos
path: attacker transfers wstETH directly to strategy -> keeper calls TokenizedStrategy.report() -> BaseLSTAccumulator._harvestAndReport() calls `_stake(0)` when no WETH can be staked -> Strategy4626._stake() deposits the forced loose wstETH into the downstream vault -> capped ERC4626 vault reverts -> report and healthcheck cannot complete
seam: three-way (execution x periphery x first-principles)
trace: `_harvestAndReport()` chooses `Math.min(balanceOfAsset(), availableDepositLimit(address(this)))`; with `balanceOfAsset() == 0` and/or downstream `vault.maxDeposit(address(this)) == 0`, the chosen amount is zero, but the Strategy4626 override still checks `balanceOfWstETH()` and calls `vault.deposit(wstETHBalance, address(this))`.
violated_principle: forced token balances should not let an untrusted sender make the strategy's reporting path depend on downstream vault deposit capacity; reports should be able to value loose wstETH even when new vault deposits are closed.
proof: Take a Strategy4626 whose downstream ERC4626 vault currently returns `maxDeposit(address(strategy)) == 0`, a normal capped-vault state already respected by Strategy4626.availableDepositLimit(). Let `pendingRedemptions == 0`, `balanceOfAsset() == 0`, and `balanceOfWstETH() == 0`. An attacker transfers 1 wei of wstETH to the strategy. On the next report, `_harvestAndReport()` calls `_stake(0)`. `super._stake(0)` returns, `stethBalance` can be zero, `wstETHBalance == 1`, and the strategy calls `vault.deposit(1, address(this))`. ERC4626 deposit is required to revert when all assets cannot be deposited due to a deposit limit, and OpenZeppelin's implementation enforces `assets <= maxDeposit(receiver)`, so a capped vault reverts. The attacker can repeat this with 1 wei of wstETH whenever the vault is closed or donate enough loose wstETH to exceed a smaller nonzero cap.
description: Strategy4626's zero-amount stake path still sweeps loose wstETH into the downstream vault, allowing a dust wstETH transfer to DoS reports whenever the vault cannot accept that dust.
fix: In Strategy4626._stake(), cap the vault sweep by `vault.maxDeposit(address(this))` and skip the deposit when capacity is zero, or leave loose wstETH valued in-place instead of making reports require a successful downstream deposit.

FINDING | contract: BaseLSTAccumulator | function: availableDepositLimit | bug_class: pending-redemption-deposit-cap-bypass | group_key: BaseLSTAccumulator | availableDepositLimit | pending-redemption-deposit-cap-bypass
path: management initiates Lido withdrawal -> stETH leaves held balances and `pendingRedemptions` records the claim -> open/allowed depositor calls deposit while redemption is pending -> TokenizedStrategy.deposit() checks `availableDepositLimit(receiver)` -> `_depositLimit()` ignores queued value because `estimatedTotalAssets()` excludes pending Lido claims -> deposit is accepted and deployed -> later queue claim returns WETH -> actual WETH-equivalent exposure exceeds `depositLimit`
seam: three-way (execution x periphery x first-principles)
trace: Lido queue request moves value out of `balanceOfLST()` while `pendingRedemptions > 0`; deposits are not blocked by `pendingRedemptions`; TokenizedStrategy enforces deposits with `_maxDeposit() -> availableDepositLimit(receiver)` and then `_deposit() -> deployFunds(asset.balanceOf(strategy))`; after the Lido claim, the hidden queued value becomes idle WETH again.
violated_principle: `depositLimit` is the management TVL/risk cap and should not be bypassable merely because existing strategy value is temporarily represented by Lido queue claims.
proof: Set `depositLimit = 100e18`, `reportBuffer = 0`, `openDeposits = true`, and assume the strategy holds 100e18 stETH with no idle WETH, so `estimatedTotalAssets() == 100e18` and `availableDepositLimit(user) == 0`. Management calls `initiateLSTWithdrawal(100e18)`: `pendingRedemptions` becomes 100e18 and the stETH is transferred to the Lido queue, so `balanceOfLST() == 0` and `estimatedTotalAssets() == 0` while the queue claim is outstanding. Now `availableDepositLimit(user)` returns 100e18. A user deposits 100e18 WETH; TokenizedStrategy accepts it because `assets <= _maxDeposit()`, transfers it, increments stored total assets, and calls `deployFunds()`, which stakes the WETH into stETH. When the keeper later claims the Lido withdrawal, the strategy also receives about 100e18 WETH and clears `pendingRedemptions`. The strategy now has about 200e18 WETH-equivalent value against a 100e18 deposit limit; the second 100e18 deposit would have been rejected if pending queue value had counted toward the cap.
description: Lido queue value is excluded from the deposit-limit calculation while deposits remain open, so any open/allowed depositor can enter capacity that only appears because redemptions are pending.
fix: Include `pendingRedemptions` in the cap basis used by `_depositLimit()` or return zero deposit capacity while `pendingRedemptions != 0`.

LEAD | contract: Strategy | function: _initiateLSTWithdrawal/_claimLSTWithdrawal | bug_class: queue-claimdata-shape-mismatch | group_key: Strategy | Lido queue handoff | queue-claimdata-shape-mismatch
code_smells: `_initiateLSTWithdrawal()` returns `abi.encode(requestIds)` where `requestIds` is a `uint256[]`, but `_claimLSTWithdrawal()` decodes `_claimData` as a single `uint256`. If the returned bytes are passed directly into `claimLSTWithdrawal()`, ABI decoding reads the dynamic-array offset `0x20` as the request id and attempts to claim request 32 instead of the actual id. The repo tests work around this by decoding the returned `uint256[]` and passing `abi.encode(requestIds[0])`.
description: The public request/claim handoff is not self-consistent; confirm whether off-chain keeper tooling always decodes and re-encodes the first id, otherwise the normal claim path can leave `pendingRedemptions` stuck until manual correction.

LEAD | contract: Strategy4626 | function: _freeStETH | bug_class: overbroad-loose-wsteth-unwrap | group_key: Strategy4626 | _freeStETH | overbroad-loose-wsteth-unwrap
code_smells: `_freeStETH(_amount)` computes `neededWstETH` for the requested shortfall, but after optional vault redemption it calls `wstETH.unwrap(wrappedBalance)` using the entire loose wstETH balance. If prior emergency/manual flows left a large loose wstETH balance, a small swap or withdrawal request can unwrap all of it, while the caller's downstream operation only swaps or queues `Math.min(_amount, balanceOfLST())`.
description: This is an extra state transition in the stETH->wstETH->vault unwind path; impact remains partial because roles can intentionally recover by later reporting/restaking or swapping, but the function changes more position state than the requested amount implies.

LEAD | contract: Strategy4626Factory | function: newStrategy4626 | bug_class: external-call-before-registry-write | group_key: Strategy4626Factory | newStrategy4626 | external-call-before-registry-write
code_smells: The permissionless `_vault` is called through `ERC20(_vault).symbol()` and again through `IERC4626(_vault).asset()` during `new Strategy4626(...)` before `deployments[_vault]` is written. A malicious vault can reenter `newStrategy4626(_vault)` while `deployments[_vault] == address(0)`, causing multiple live strategies and multiple `NewStrategy4626` events for the same vault before the last returning frame overwrites the registry mapping.
description: This breaks the intended one-strategy-per-vault registry invariant for adversarial vaults, but I kept it as a lead because the created strategies still receive factory role defaults and the confirmed impact is registry/event ambiguity unless a downstream consumer treats orphan events as canonical.
