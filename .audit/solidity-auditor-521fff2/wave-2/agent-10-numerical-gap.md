# Agent 10 - Numerical Gap Hunter

Scope: BaseLSTAccumulator, Strategy, Strategy4626, Strategy4626Factory, StrategyAprOracle at commit 521fff28ad978a37115be8995a1d631611fa1d3d.

## Tool markers

[Feynman: BaseLSTAccumulator] This contract is the shared accounting shell. It receives WETH, optionally turns WETH into the liquid staking token, reports a haircut value for idle WETH plus staking-token exposure, and forces normal withdrawals to use only WETH already sitting in the strategy.

[Feynman: estimatedTotalAssets] This function tells Yearn how much WETH-equivalent value the strategy believes it owns. It counts WETH exactly and counts the staking-token side after subtracting a configurable haircut.

[Socratic: BaseLSTAccumulator:178 - why?] Why can `MAX_BPS - reportBuffer` be trusted? The code assumes management keeps `reportBuffer` inside basis-point scale; there is no numerical guard, so this is an operator-only bricking edge rather than an untrusted path.

[Inversion: estimatedTotalAssets] 1. Set the haircut above 10,000 bps and make the subtraction revert. 2. Feed `valueOfLST()` a downstream vault value that ignores exit fees. 3. Queue a redemption so reports cannot use the value path until pending state is cleared.

[Feynman: _harvestAndReport] This function refuses to report while a Lido withdrawal is pending, sells any rewards, stakes idle WETH up to the strategy's deposit room, then returns the strategy's estimated value.

[Socratic: BaseLSTAccumulator:152 - why?] Why is idle WETH staked up to `availableDepositLimit(address(this))` instead of a value that already accounts for staking-route surplus? The code assumes the amount of WETH sent into staking maps to no more than the downstream vault room.

[Feynman: initiateLSTWithdrawal] This management function chooses an amount no larger than the strategy's reported staking-token value, records that amount as pending, then asks the child contract to queue the actual withdrawal.

[Feynman: claimLSTWithdrawal] This keeper function claims one completed withdrawal, measures how much ETH arrived, wraps all ETH into WETH, and reduces the pending counter by the ETH amount received.

[Inversion: claimLSTWithdrawal] 1. Claim a request that finalizes below the queued stETH amount so pending remains nonzero and reports stay blocked. 2. Pass the dynamic-array return bytes from initiation directly and make the scalar decode target the ABI offset instead of the request id. 3. Preload stray ETH so the function sweeps more ETH to WETH than it subtracts from pending.

[Feynman: Strategy._stake] This function turns WETH into ETH, checks whether Curve currently gives more stETH than direct Lido staking, then either swaps through Curve with a 1:1 minimum or submits ETH to Lido.

[Socratic: Strategy:58 - why?] Why is `get_dy > amount` only used as a route choice and not fed into later capacity math? The strategy assumes surplus stETH is always acceptable, but Strategy4626 may immediately deposit all wrapped surplus into a capped vault.

[Inversion: Strategy._stake] 1. Make Curve quote a tiny surplus over 1:1 at the downstream vault cap. 2. Let direct staking fit the cap but Curve output exceed it. 3. Use a stale-friendly `get_dy` branch where the swap succeeds at the 1:1 floor but downstream vault capacity was computed from the input amount.

[Feynman: Strategy._swapLSTToAsset] This function approves stETH to Curve, swaps stETH for ETH using the caller's minimum output, then wraps the strategy's whole ETH balance into WETH.

[Feynman: Strategy._claimLSTWithdrawal] This function decodes a single request id, claims that request from Lido's queue, calculates the ETH that arrived during the claim, and wraps ETH into WETH.

[Feynman: Strategy4626] This variant adds a second layer: after getting stETH, it wraps stETH into wstETH and deposits wstETH into another ERC4626 vault.

[Feynman: Strategy4626._stake] This function performs the normal stETH acquisition, wraps every stETH token the strategy holds into wstETH, then deposits every wstETH token the strategy holds into the downstream vault.

[Inversion: Strategy4626._stake] 1. Start exactly at the downstream vault's remaining deposit room. 2. Route through Curve so the strategy receives more stETH than the WETH input. 3. Include loose old stETH/wstETH so a new small stake pushes the all-balance deposit over the vault cap.

[Feynman: Strategy4626.availableDepositLimit] This function tells Yearn how much WETH a receiver may deposit. It first applies the base strategy limit, then limits that by the downstream vault's remaining wstETH deposit room converted into stETH-value units.

[Socratic: Strategy4626:62 - why?] Why does `_stETHValue(maxDeposit)` equal a safe WETH deposit amount? It is only safe if staking produces no more stETH value than the WETH input and if all existing loose balances are zero or already included.

[Inversion: Strategy4626.availableDepositLimit] 1. Use a finite `vault.maxDeposit`. 2. Deposit the exact returned limit while Curve gives a premium. 3. Leave tiny loose wstETH so the function returns capacity for new flow but `_stake` deposits the whole balance.

[Feynman: Strategy4626.valueOfWstETH] This function prices loose wstETH plus the downstream vault shares as stETH value, using the vault's ideal share-to-asset conversion for the vault position.

[Socratic: Strategy4626:70 - why?] Why is `convertToAssets(vault.balanceOf(this))` the same number the strategy can actually free? ERC4626 explicitly lets `convertToAssets` ignore fees and live exit conditions, while redeem previews include withdrawal fees.

[Inversion: Strategy4626.valueOfWstETH] 1. Use a compliant vault with a redeem fee. 2. Use a vault where `maxRedeem` is temporarily lower than the share balance. 3. Use rounding where `convertToAssets` reports one more unit than a redeem path can return.

[Feynman: Strategy4626._freeStETH] This function makes sure enough plain stETH is available by unwrapping loose wstETH and redeeming vault shares if needed, with a two-wei buffer for wrapping roundoff.

[Socratic: Strategy4626:88 - why?] Why use `previewWithdraw` to choose shares and then call `redeem` with those shares? The code wants a round-up share amount for enough wstETH, but `redeem` may still return less when fees or external vault conditions apply.

[Inversion: Strategy4626._freeStETH] 1. Ask for an amount just above direct stETH balance. 2. Make preview/redeem differ because of fees. 3. Let `maxRedeem` cap shares below the preview amount and check whether the caller notices shortfall.

[Feynman: Strategy4626Factory.newStrategy4626] This function lets anyone create one Strategy4626 for a chosen vault, as long as that vault says its asset is wstETH, then stamps the factory's role defaults onto the new strategy.

[Feynman: StrategyAprOracle.aprAfterDebtChange] This function always returns a fixed 4% APR number in 1e18 units and ignores the strategy and debt-change inputs.

## Findings

No confirmed numerical-gap FINDINGs.

## Leads

LEAD | contract: Strategy4626 | function: valueOfWstETH/_freeStETH | bug_class: erc4626-fee-blind-valuation | group_key: Strategy4626 | valueOfWstETH | erc4626-fee-blind-valuation
code_smells: `valueOfWstETH()` values vault shares with `vault.convertToAssets(vault.balanceOf(address(this)))`, but ERC4626 `convertToAssets` is defined as an ideal conversion that must not include fees or live exit conditions; the freeing path later uses `previewWithdraw`, `maxRedeem`, and `redeem`, whose previews are fee-inclusive. Concrete seam: with 100 vault shares at 1 wstETH/share and a compliant 10% exit fee, `convertToAssets(100e18) = 100e18`, so `estimatedTotalAssets()` reports 100e18 wstETH-equivalent before the stETH conversion, while `redeem(100e18)` can return only 90e18 wstETH. The invariant "reported vault assets equal freeable vault assets" holds for a no-fee vault but breaks across the precision/invariant seam once the ERC4626 ideal conversion and redeem preview are allowed to diverge.
description: A Strategy4626 deployed against a fee-on-redeem or otherwise unfavorable wstETH ERC4626 vault can overstate reported assets because reporting uses `convertToAssets` while exits use redeem semantics; this needs confirmation against the intended downstream vault set before escalating beyond a lead.

LEAD | contract: Strategy4626 | function: availableDepositLimit/_stake | bug_class: max-deposit-route-surplus | group_key: Strategy4626 | availableDepositLimit | max-deposit-route-surplus
code_smells: `availableDepositLimit()` converts `vault.maxDeposit(address(this))` from wstETH units into stETH value and returns that as a safe WETH deposit cap, but `_stake()` can choose Curve when `get_dy(ETH, stETH, amount) > amount` and then deposits the entire resulting wstETH balance into the vault. Concrete seam: if `vault.maxDeposit(this) = 100e18 wstETH`, wstETH is 1.2 stETH/wstETH, and `availableDepositLimit()` returns `_stETHValue(100e18) = 120e18`, a 120e18 WETH stake fits the advertised cap only under 1:1 output. If Curve returns 121.2e18 stETH, wrapping yields about 101e18 wstETH, so `vault.deposit(101e18, this)` crosses the 100e18 maxDeposit boundary and reverts. OpenZeppelin ERC4626 implementations enforce `assets <= maxDeposit(receiver)` during deposit.
description: The deposit-limit view can advertise a boundary amount that the write path cannot accept whenever the chosen staking route produces surplus stETH or existing loose balances are swept into the all-balance vault deposit.

## Checked but not reported

- `reportBuffer`: setting `reportBuffer > MAX_BPS` underflows `MAX_BPS - reportBuffer` and bricks `estimatedTotalAssets()`/reports, but this is onlyManagement and did not chain to an untrusted numerical path, so it is not reported under the shared "admin-only functions doing admin things" rule.
- `pendingRedemptions`: the main state unit is stETH queued and the decrement unit is ETH received. For normal 1:1 Lido finalization the numbers clear; for below-par finalization the residual pending value intentionally blocks reports until management clears realized loss. No untrusted precision gap was proven.
- `claimLSTWithdrawal` claim-data shape: `initiateLSTWithdrawal()` returns `abi.encode(uint256[])`, while `_claimLSTWithdrawal()` expects `abi.encode(uint256)`. Repo tests decode the returned array and re-encode `requestIds[0]` before claiming, so this is a sharp integration expectation but not a numerical-gap finding for this lane.
- `StrategyAprOracle`: `4e16` matches 4% APR in 1e18 units. Ignoring `_strategy` and `_delta` is an oracle-quality limitation, not a numerical seam with exploit proof in this scope.
