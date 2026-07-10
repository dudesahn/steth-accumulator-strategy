# Lane 2 - Access Control

[Feynman: BaseLSTAccumulator]
This base strategy keeps WETH deposits either idle or converted into the liquid-staking position. It also owns the custom management knobs: deposit openness, whitelisting, report haircut, manual staking, manual unstaking, Lido queue initiation, keeper claims, and emergency pending-redemption cleanup. The important permission boundary is that normal users only enter through inherited ERC4626 functions, while management and keeper roles decide when liquidity is moved between WETH, stETH, wstETH, the downstream vault, and Lido queue claims.

[Feynman: availableDepositLimit]
This function answers "can this receiver get more shares right now?" If deposits are globally open or the receiver is whitelisted, it returns the remaining strategy capacity; otherwise it returns zero. The fuzzy spot is that the checked address is the share receiver, not necessarily the caller funding the deposit, but an unauthorized caller can only donate shares to an allowed receiver.

[Inversion: availableDepositLimit]
1. Deposit with `receiver` set to an allowed address while `msg.sender` is unallowed: funds come from the caller and shares go to the allowed receiver, so this is a donation, not bypass profit.
2. Deposit to `address(this)` because the strategy is self-allowed: inherited `_maxDeposit` blocks receiver `address(this)` before calling this limit.
3. Close deposits and unset `allowed[address(this)]`: this can stop harvest restaking but requires management.

[Feynman: _harvestAndReport]
This report path refuses to run while Lido withdrawals are pending, sells rewards if any, stakes idle WETH up to the self deposit limit, then reports the current WETH-equivalent value. The access boundary is inherited `report()` being keeper-or-management only and the callback being self-only.

[Inversion: _harvestAndReport]
1. Have an unprivileged caller invoke `harvestAndReport()` directly: `onlySelf` rejects it.
2. Have a keeper call `report()` while `pendingRedemptions > 0`: the strategy-level require rejects it.
3. Have management close deposits to block self-staking during report: this is management-configured behavior, not unauthorized access.

[Feynman: management setters]
The setters change strategy parameters that affect deposits, reporting, tending, and manual movement of funds. They all use `onlyManagement`, which resolves through TokenizedStrategy storage and requires the current management address.

[Inversion: management setters]
1. Call a custom setter from an unprivileged account: TokenizedStrategy.requireManagement rejects it.
2. Call an inherited setter selector through fallback from an unprivileged account: the inherited `onlyManagement` modifier rejects it.
3. Try to use the factory after deployment as child management: the child starts with `management == factory`, but the factory exposes no generic forwarding function.

[Feynman: manualSwapToAsset]
Management asks the strategy to turn up to a requested amount of LST value back into WETH, with a management-chosen minimum output. This is a privileged liquidity operation; it does not transfer assets to management.

[Feynman: manualStake]
Management asks the strategy to stake up to a requested amount of idle WETH. This moves assets into the yield-side position but keeps them owned by the strategy.

[Feynman: initiateLSTWithdrawal]
Management starts a Lido withdrawal by increasing the aggregate pending-redemption counter and then asking the Lido queue for a withdrawal request owned by the strategy. The returned request IDs are handed back to the caller but are not stored by this contract.

[Feynman: claimLSTWithdrawal]
A keeper or manager supplies claim data, the strategy claims one Lido queue request, wraps all ETH received into WETH, then decreases the aggregate pending-redemption counter by the ETH amount observed. The fuzzy spot is that the claim data is not tied to a stored request ID or amount.

[Inversion: claimLSTWithdrawal]
1. Keeper supplies an unrelated request ID not owned by the strategy: expected to revert or transfer no ETH, depending on Lido queue ownership rules.
2. Keeper supplies a different strategy-owned request ID than the one management just initiated: pending is reduced by received ETH, not by a stored per-request amount.
3. Someone donates a completed withdrawal claim to the strategy, then keeper claims it to reduce pending: requires donated value and Lido ownership semantics, so not proven as an attack here.

[Feynman: clearPendingRedemptions]
Management manually lowers the pending-redemption counter. This can unblock reports after Lido queue trouble, but it is explicitly management-only and can realize losses if misused.

[Feynman: Strategy]
The stETH strategy converts WETH to ETH, chooses Curve when it is better than one-to-one, otherwise submits to Lido, and can reverse stETH to WETH through Curve. Its only first-party state setter is the referral address, guarded by management. The emergency claim path lets emergency-authorized callers batch-claim Lido withdrawals and optionally zero pending redemptions.

[Inversion: Strategy emergency paths]
1. Unprivileged caller invokes `manualClaimWithdrawals`: inherited emergency authorization rejects it.
2. Emergency admin claims before shutdown: allowed by this custom function, but assets are wrapped back into WETH inside the strategy.
3. Emergency admin zeros pending redemptions without a matching claim: privileged emergency behavior already mirrored by management's clear function.

[Feynman: Strategy4626]
The 4626 extension takes any stETH obtained by the base strategy, wraps it to wstETH, and deposits it into a downstream ERC4626 vault whose asset must be wstETH. Emergency-authorized callers can redeem vault shares or unwrap wstETH back to stETH, but these actions keep assets in the strategy.

[Inversion: Strategy4626 emergency frees]
1. Unprivileged caller invokes `manualRedeem` or `manualUnwrap`: emergency authorization rejects it.
2. Emergency admin redeems/unwraps during normal operation: composition changes but the strategy remains the receiver.
3. Malicious downstream vault is selected at deployment: constructor only checks `asset() == wstETH`; this is a factory/deployment trust boundary rather than a direct role bypass.

[Feynman: Strategy4626Factory]
The factory stores default role addresses and lets anyone deploy one Strategy4626 per vault. A new child initially has the factory as current management because the factory deploys it, then the factory calls inherited setters to stamp keeper, emergency admin, fee recipient, fee, unlock time, and pending management. The intended management address must later accept management on the child.

[Socratic: Strategy4626Factory.newStrategy4626 - why permissionless?]
The implicit belief is that a factory deployment is not itself an endorsement of the chosen vault, because the caller controls `_vault` and the only code check is that the vault reports wstETH as its asset.

[Inversion: newStrategy4626]
1. Call with a malicious ERC4626 vault whose `asset()` returns wstETH: the factory deploys and records a strategy unless some later external call reverts.
2. Call before an operator rotates factory defaults: the child receives whatever role defaults are live at that block, and the one-per-vault mapping blocks replacement.
3. Try to reenter through `symbol()` or `asset()`: those calls are typed as view/static calls, so state-changing reentry into the factory should fail.

[Feynman: setAddresses]
The current factory management address can replace future deployment defaults. This does not update already deployed children.

[Inversion: setAddresses]
1. Unprivileged caller tries to rotate defaults: the inline `msg.sender == management` check rejects it.
2. Management sets a zero pending-management or fee-recipient default: later deployments revert in inherited setters, a management-caused deployment DoS.
3. Management sets a stale keeper or emergency admin: future permissionless deployments stamp that value until defaults are rotated.

[Feynman: TokenizedStrategy delegatecall access]
The custom strategy uses a fixed TokenizedStrategy implementation through fallback. Role checks read strategy-local storage during delegatecall, and custom callbacks are protected by `onlySelf`, so direct external callers cannot reach deploy, free, report, tend, or shutdown-withdraw callbacks.

[Inversion: delegatecall role boundary]
1. Directly call `deployFunds`, `freeFunds`, `harvestAndReport`, `tendThis`, or `shutdownWithdraw`: `msg.sender` is not the strategy itself, so `onlySelf` rejects.
2. Call inherited role setters through fallback from an unprivileged address: inherited role modifiers reject.
3. Look for custom selector collisions with inherited management functions: the test suite checks the relevant inherited selectors and role reverts.

[Feynman: StrategyAprOracle]
The APR oracle returns a fixed value for any strategy and debt change. Governance exists only through the inherited base for governance transfer; the APR function itself is view-only and has no write access.

No FINDING blocks emitted.

LEAD | contract: Strategy4626Factory | function: newStrategy4626 | bug_class: permissionless-role-stamping | group_key: Strategy4626Factory | newStrategy4626 | permissionless-role-stamping
code_smells: `newStrategy4626` is external and permissionless, `_vault` is caller-controlled, the Strategy4626 constructor checks only that `IERC4626(_vault).asset() == wstETH`, and the factory immediately stamps the child with the factory's live role defaults before recording `deployments[_vault]`. The factory test confirms the child starts with `management == address(factory)` and `pendingManagement == factory.management()`, so an arbitrary caller can create the one registered factory strategy for a vault before any off-chain allowlist, deployment reservation, or role-default update. This is not a FINDING because the caller does not gain management, keeper, or emergency-admin rights from the code alone, and I did not prove that any downstream integration treats `NewStrategy4626` or `isDeployedStrategy` as a safety endorsement.
description: Permissionless one-per-vault deployment plus official role stamping is a registry/trust-boundary lead for arbitrary wstETH ERC4626 vaults, but needs an external endorsement or deployment-sequencing assumption to become exploitable.

LEAD | contract: BaseLSTAccumulator | function: claimLSTWithdrawal | bug_class: unbound-keeper-claim-data | group_key: BaseLSTAccumulator | claimLSTWithdrawal | unbound-keeper-claim-data
code_smells: `initiateLSTWithdrawal` only stores an aggregate `pendingRedemptions += _amount` and returns the Lido request IDs to the caller; it does not persist request IDs or per-request amounts. `claimLSTWithdrawal(bytes)` lets a keeper or management-sender supply arbitrary claim data, Strategy decodes it as a request ID, and the base contract decreases pending redemptions only by the ETH balance delta observed after the claim. The reachable role boundary is therefore "keeper can claim any claimable strategy-owned request that produces ETH" rather than "keeper can only claim the specific request IDs management initiated." This is not a FINDING because I did not prove, from in-repo code, that a non-management actor can create or transfer a claimable strategy-owned Lido request in a way that harms the strategy without donating equivalent value.
description: Keeper-controlled claim data is not bound to stored management-initiated Lido requests, leaving a partial path for pending-redemption accounting manipulation that depends on external Lido ownership and claim-transfer semantics.
