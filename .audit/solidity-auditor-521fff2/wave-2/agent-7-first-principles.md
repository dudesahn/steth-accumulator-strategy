# Solidity Auditor Lane 7 - First Principles

Repo: `/Users/dudesahn/Documents/GitHub/codex/review/steth-accumulator-strategy`
Commit: `521fff28ad978a37115be8995a1d631611fa1d3d`
Bundle: `.audit/solidity-auditor-521fff2/bundles/agent-7-bundle.md`

Verdict: no FINDING blocks emitted. I found several real assumption breaks, but each depends on a bounded role, an accepted test/spec behavior, or an external vault condition rather than an unguarded value-extracting path.

## Working Markers

[Feynman: BaseLSTAccumulator]
This contract is the strategy's steering layer. WETH enters through the Yearn strategy wrapper, this layer decides whether WETH is left liquid or turned into LST exposure, it limits deposits and withdrawals, and it reports how much WETH-equivalent value the strategy thinks it controls. The fuzzy spot is that "value controlled" and "value liquid for users" are intentionally different things here.

[Feynman: BaseLSTAccumulator._deployFunds]
When new WETH arrives from a deposit, this function either leaves it alone or turns it into LST exposure. The switch named `stakeAsset` is honored here, so disabling the switch makes deposits leave WETH idle.

[Feynman: BaseLSTAccumulator._harvestAndReport]
On report, the strategy refuses to continue if a Lido redemption is still pending, claims any reward path, moves idle WETH into LST exposure up to the current deposit limit, and returns the accounting number used by Yearn. The fuzzy spot is that this function stakes idle WETH even when the separate staking switch is off.

[Socratic: BaseLSTAccumulator.sol:150 - why?]
Why does report stake loose WETH without checking `stakeAsset`? The implicit belief is that reports should always redeploy idle assets, while the switch only controls deposit-time staking.

[Inversion: BaseLSTAccumulator._harvestAndReport]
1. Management sets `stakeAsset = false`, user deposits 10 WETH, keeper reports, and the report still stakes the 10 WETH.
2. Management leaves WETH idle for withdrawal liquidity, keeper calls `tend()`, and `_tend` stakes the full idle balance.
3. Deposits are closed for users, but `allowed[address(this)]` remains true, so report can still redeploy strategy-owned idle WETH.

[Feynman: BaseLSTAccumulator._tend]
This function lets a keeper move currently idle WETH into LST exposure between reports. It does not ask whether management disabled deposit-time staking.

[Feynman: BaseLSTAccumulator.availableWithdrawLimit]
This function tells users they can withdraw only the WETH already sitting in the strategy. It does not promise that stETH, wstETH, or vault shares will be freed for normal withdrawals.

[Feynman: BaseLSTAccumulator._emergencyWithdraw]
After shutdown, this function tries to turn direct stETH held by the strategy into WETH. If there is no direct stETH balance, it stops immediately. The fuzzy spot is that the 4626 strategy normally holds value one layer deeper than direct stETH.

[Socratic: BaseLSTAccumulator.sol:159 - why?]
Why does emergency withdrawal start from `balanceOfLST()` rather than total LST value? The implicit belief is that emergency-recoverable LST value is direct stETH, which is not true for the 4626 variant.

[Inversion: BaseLSTAccumulator._emergencyWithdraw]
1. Strategy4626 has all value in downstream vault shares, direct stETH is zero, shutdown happens, and `emergencyWithdraw` returns without freeing value.
2. Strategy4626 has loose wstETH but no stETH, shutdown happens, and `emergencyWithdraw` still returns without unwrapping.
3. Strategy4626 has less direct stETH than requested but more value in vault shares, and `emergencyWithdraw` only swaps the direct stETH slice.

[Feynman: Strategy]
This contract turns WETH into stETH either through Curve or direct Lido staking, turns stETH back into WETH through Curve, and talks to the Lido withdrawal queue. It is the bridge between WETH accounting and ETH/stETH external systems.

[Feynman: Strategy._stake]
This function unwraps WETH into ETH, checks whether Curve can buy more stETH than direct staking, and then either swaps through Curve with a 1:1 minimum or stakes directly into Lido. The assumption is that the chosen route can always accept the whole amount.

[Feynman: Strategy._initiateLSTWithdrawal]
This function approves stETH to the Lido queue, asks for one withdrawal request, and returns the request id array encoded as bytes.

[Feynman: Strategy._claimLSTWithdrawal]
This function expects claim data to contain one request id, asks Lido to claim that request, measures the ETH received, and wraps all ETH in the strategy into WETH. The fuzzy spot is that the previous initiation function returned an encoded array, not an encoded single id.

[Socratic: Strategy.sol:105 - why?]
Why does claim decode `bytes` as a single `uint256` when initiation returned `abi.encode(uint256[])`? The implicit belief is that callers will transform the initiation return data before claiming.

[Inversion: Strategy._claimLSTWithdrawal]
1. Keeper passes the raw initiation return data and the decoder reads the ABI offset word (`32`) as the request id.
2. Keeper claims a different strategy-owned request id and pending redemptions are decremented by whatever ETH that request returns.
3. Claim returns less ETH than the pending amount and reporting remains blocked until management clears or another claim catches up.

[Feynman: Strategy4626]
This variant takes stETH exposure, wraps it into wstETH, and deposits that wstETH into another ERC4626 vault. The strategy's value can therefore live as direct stETH, loose wstETH, or shares in the downstream vault.

[Feynman: Strategy4626._stake]
This function first performs the normal WETH-to-stETH route, then wraps any stETH it has, then deposits all loose wstETH into the downstream vault. It deposits the output amount, not just the original WETH input amount.

[Feynman: Strategy4626.availableDepositLimit]
This function asks the downstream vault how much wstETH it will accept, converts that capacity into stETH terms, and returns the smaller of that amount and the base strategy limit. The fuzzy spot is that WETH can become more than the same amount of stETH through Curve.

[Socratic: Strategy4626.sol:58 - why?]
Why is a wstETH max-deposit cap converted into a WETH deposit cap without considering Curve bonus output? The implicit belief is that one WETH maps to no more than one stETH of downstream capacity.

[Inversion: Strategy4626.availableDepositLimit]
1. Downstream vault has exactly 100 wstETH of remaining `maxDeposit`, strategy accepts 100 WETH, Curve returns more than 100 stETH, and `vault.deposit(allWstETH)` can exceed capacity.
2. A report stakes idle WETH up to the returned cap, but the route output is above cap and the report reverts.
3. The downstream vault returns a stale or overly optimistic `maxDeposit`, and the strategy only discovers the mismatch after it has converted WETH to stETH/wstETH.

[Feynman: Strategy4626._freeStETH]
This helper tries to make enough direct stETH available by using loose stETH first, then loose wstETH, then redeeming downstream vault shares if needed, and finally unwrapping wstETH. The assumptions are that the vault's preview and redeem behavior line up, and that freeing more than the requested amount is acceptable.

[Feynman: Strategy4626Factory]
This contract deploys one 4626 accumulator per chosen vault, using the factory's current role defaults. Anyone can start deployment, but the configured pending management still has to accept the strategy before normal management actions are usable.

[Feynman: Strategy4626Factory.newStrategy4626]
This function checks that the vault has not already been used, builds a name from the vault symbol, deploys a strategy, stamps role/default settings from the factory, records the deployment, and returns the new strategy. The fuzzy spot is that the single deployment slot is consumed by whoever calls first.

[Inversion: Strategy4626Factory.newStrategy4626]
1. A caller deploys for a legitimate vault before planned factory role rotation, permanently binding that vault's factory slot to the old defaults.
2. A caller deploys for a malicious but wstETH-asset vault, making `isDeployedStrategy` true for a strategy that should not be treated as endorsed without management review.
3. A caller deploys while pending management is unable or unwilling to accept, leaving factory as current management with no general forwarding surface.

## Leads

LEAD | contract: BaseLSTAccumulator | function: _harvestAndReport,_tend | bug_class: stake-toggle-bypass | group_key: BaseLSTAccumulator | _harvestAndReport,_tend | stake-toggle-bypass
code_smells: `stakeAsset` gates `_deployFunds()` but does not gate keeper-reachable `report()` or `tend()`; `TokenizedStrategy.report()` is `onlyKeepers` and calls `harvestAndReport()`, while `TokenizedStrategy.tend()` is `onlyKeepers` and forwards the current idle WETH balance to `tendThis()`. The repo tests explicitly assert this behavior in `test_harvestStakesBypassesStakeAssetFlag` and `test_tendExecution`.
description: If the protocol goal of `setStakeAsset(false)` is to preserve idle WETH for withdrawals or avoid fresh LST exposure, a keeper can still convert that idle WETH into stETH through report or tend, reducing `availableWithdrawLimit()` to zero; kept as a LEAD because tests currently encode this as intended keeper behavior.

LEAD | contract: Strategy4626 | function: _emergencyWithdraw | bug_class: vault-position-not-reached | group_key: Strategy4626 | _emergencyWithdraw | vault-position-not-reached
code_smells: Strategy4626 normal deposits end as downstream vault shares with no loose wstETH in the existing test path, but the inherited shutdown withdrawal helper only checks direct stETH via `balanceOfLST()` and returns when that balance is zero. `TokenizedStrategy.emergencyWithdraw()` only forwards to `shutdownWithdraw(amount)`, so the one-call emergency path cannot reach vault-held value.
description: In a shutdown, `emergencyWithdraw()` alone is a no-op for the common Strategy4626 state where value is in vault shares; kept as a LEAD because emergency-authorized accounts can manually `manualRedeem()` and `manualUnwrap()` first, then use the shutdown path once stETH is loose.

LEAD | contract: Strategy | function: _initiateLSTWithdrawal,_claimLSTWithdrawal | bug_class: claim-data-shape-mismatch | group_key: Strategy | _initiateLSTWithdrawal,_claimLSTWithdrawal | claim-data-shape-mismatch
code_smells: `_initiateLSTWithdrawal()` returns `abi.encode(requestIds)` where `requestIds` is a `uint256[]`, but `_claimLSTWithdrawal()` decodes its input as a single `uint256`. The local withdrawal tests must decode the array and re-encode `requestIds[0]`; passing the raw initiation return data would decode the first word as the dynamic array offset (`32`) rather than the Lido request id.
description: The request and claim data formats are desynchronized and can keep `pendingRedemptions` stuck until a keeper supplies manually transformed claim data; kept as a LEAD because the keeper/management role can recover with the correct encoding and I did not identify value extraction.

LEAD | contract: Strategy4626 | function: availableDepositLimit,_stake | bug_class: downstream-capacity-mismatch | group_key: Strategy4626 | availableDepositLimit,_stake | downstream-capacity-mismatch
code_smells: `availableDepositLimit()` converts the downstream vault's `maxDeposit(address(this))` from wstETH capacity into stETH value and returns that as WETH deposit capacity, but `_stake()` can route through Curve when ETH-to-stETH output is greater than the WETH input, then Strategy4626 wraps and deposits the full output balance. A cap-compliant WETH amount can therefore produce more wstETH than the downstream vault said it would accept.
description: During finite downstream-vault capacity and favorable Curve pricing, a deposit/report/tend path can revert after converting WETH to more wstETH than the cap allowed; kept as a LEAD because this depends on a concrete external vault cap and live Curve state rather than an in-repo proof.

LEAD | contract: Strategy4626Factory | function: newStrategy4626 | bug_class: permissionless-one-shot-defaults | group_key: Strategy4626Factory | newStrategy4626 | permissionless-one-shot-defaults
code_smells: `newStrategy4626()` is permissionless, consumes the sole `deployments[_vault]` slot, snapshots mutable factory role defaults, and leaves the factory as current strategy management until the configured pending management accepts; factory tests assert `strategy.management() == address(factory)` immediately after deployment.
description: Anyone can consume the one factory deployment slot for a vault using whatever defaults are live at that moment, which can create stale-role or registry-confusion risk; kept as a LEAD because deposits remain closed until management accepts/configures the strategy and no direct fund loss path was proven.

## Checked But Not Emitted

- `reportBuffer > MAX_BPS` can make accounting views/reports revert through checked subtraction, but this is a direct management-only misconfiguration path.
- The fixed `StrategyAprOracle` APR ignores `_strategy` and `_delta`, but I found no in-scope caller that turns the illustrative oracle into a direct loss path.
- Idle-only user withdrawals are an explicit design invariant rather than a bug by themselves; the only concern is when another path unexpectedly removes the idle WETH users were relying on.
