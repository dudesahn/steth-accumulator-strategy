# Invariant Extraction

## Deposit and Mint

INV-DEP-1: A successful `deposit` or `mint` must mint nonzero strategy shares for nonzero accepted WETH.
- Relied on by: inherited ERC4626 accounting, user share ownership, withdrawal previews.
- Violated if: `_convertToShares` rounds to zero or totalAssets/totalSupply accounting is distorted.

INV-DEP-2: A successful deposit must increase TokenizedStrategy `totalAssets` by exactly the accepted WETH `assets`, independent of how much stETH/wstETH/vault value the strategy immediately receives.
- Relied on by: PPS stability and report-based profit/loss accounting.
- Violated if: `_deployFunds` reverts after transfer, deploys into an asset whose immediate value is below assumptions, or external calls cause accounting to differ from deposited WETH.

INV-DEP-3: Deposits are accepted only when the receiver passes `availableDepositLimit`, the strategy is not shutdown, and `receiver != address(this)`.
- Relied on by: deposit whitelist/limit controls and shutdown finality.
- Violated if: the receiver/owner distinction allows a disallowed receiver, or inherited maxDeposit is bypassed.

INV-DEP-4: If `stakeAsset == true` and deposited WETH exceeds `ASSET_DUST`, loose WETH should be converted to stETH/wstETH/vault exposure during `_deployFunds`.
- Relied on by: strategy yield posture and `availableWithdrawLimit` semantics.
- Violated if: staking route fails silently or leaves unexpected idle WETH.

## Withdraw and Redeem

INV-WDR-1: Withdraw/redeem may transfer only loose WETH because `_freeFunds` intentionally does nothing and `availableWithdrawLimit` returns `balanceOfAsset()`.
- Relied on by: liquid-only withdrawals and loss avoidance during stETH illiquidity.
- Violated if: inherited withdrawal logic pulls from stETH/wstETH unexpectedly or realizes losses contrary to the strategy design.

INV-WDR-2: A withdrawal/redeem must burn the owner shares and reduce TokenizedStrategy `totalAssets` by the paid assets plus any realized loss.
- Relied on by: ERC4626 share accounting.
- Violated if: external calls or fee-on-transfer behavior make paid WETH differ from accounting assumptions.

INV-WDR-3: Withdrawal receiver must be nonzero, and third-party withdrawals must consume sufficient allowance.
- Relied on by: inherited TokenizedStrategy access control.
- Violated if: approvals or permit logic can be bypassed.

## Report and Health Check

INV-RPT-1: `report()` must revert while `pendingRedemptions != 0`.
- Relied on by: avoiding accounting while stETH is queued for withdrawal and no longer fully liquid.
- Violated if: pending redemptions can be bypassed without management's explicit `clearPendingRedemptions`.

INV-RPT-2: `_harvestAndReport` must include all strategy-controlled value: loose WETH plus stETH value plus Strategy4626 wstETH/vault value, discounted by `reportBuffer`.
- Relied on by: Yearn V3 totalAssets accounting and performance fee/profit unlock logic.
- Violated if: wstETH/vault conversion or stETH share mechanics undercount/overcount assets.

INV-RPT-3: `reportBuffer` must not exceed `MAX_BPS` unless management intentionally accepts underflow/revert risk in `estimatedTotalAssets`.
- Relied on by: `(MAX_BPS - reportBuffer)` arithmetic.
- Violated if: `setReportBuffer` allows a value above `MAX_BPS`, causing view/report reverts.

INV-RPT-4: Health checks should bound unexpected profit/loss unless management explicitly disables the check for one report.
- Relied on by: `BaseHealthCheck._executeHealthCheck`.
- Violated if: management can disable checks as expected, or if reports are forced into false profit/loss from manipulated estimates.

## Staking and Swap Routes

INV-STK-1: `_stake(amount)` must convert WETH to ETH first and then receive at least `amount` stETH when using Curve or Lido direct staking.
- Relied on by: deposit/report accounting that assumes stETH is approximately WETH value.
- Violated if: Curve route can be selected based on a stale/manipulated `get_dy` but execute with less than `amount` stETH, or direct Lido staking returns less than expected.

INV-STK-2: Curve WETH->stETH path uses `_min_to_amount = amount`, so the swap should revert rather than accept below-1:1 output.
- Relied on by: no silent loss on the staking route.
- Violated if: pool behavior or ETH/WETH conversion breaks this minimum.

INV-STK-3: Manual stETH->WETH swap is management-only and must honor `_minOut` supplied by management.
- Relied on by: avoiding forced public loss realization.
- Violated if: unauthorized callers can force swaps or route through malicious pool/token behavior.

## Lido Withdrawal Queue

INV-Q-1: `initiateLSTWithdrawal` must increase `pendingRedemptions` by the queued stETH amount and transfer/lock that stETH in the Lido withdrawal queue.
- Relied on by: report blocking while queue claims are unresolved.
- Violated if: queue request reverts after state change, accepts less than `_amount`, or returns malformed request ids.

INV-Q-2: `claimLSTWithdrawal` must reduce pending redemptions by the amount of ETH actually received and wrap all ETH held by the strategy into WETH.
- Relied on by: restoring liquid WETH and unblocking reports.
- Violated if: `_claimData` decodes incorrectly, the queue claim sends ETH unrelated to the expected request, or existing ETH balance distorts claimed amount.

INV-Q-3: `manualClaimWithdrawals(..., zeroRedemptions=true)` is emergency-only and can zero pending redemptions even if the claimed amount differs from pending.
- Relied on by: emergency unstick path.
- Violated if: emergency/admin misuse masks unresolved queued stETH and causes incorrect report losses or profits.

## Strategy4626 Vault Layer

INV-4626-1: After Strategy4626 staking, all available stETH should be wrapped to wstETH, and nonzero wstETH should be deposited into the configured vault.
- Relied on by: Strategy4626 expected yield source.
- Violated if: wrapping rounds to zero, vault deposit reverts, or vault `maxDeposit`/accounting changes unexpectedly.

INV-4626-2: `valueOfWstETH` must include loose wstETH plus `vault.convertToAssets(vault.balanceOf(address(this)))`, converted back to stETH units.
- Relied on by: `estimatedTotalAssets`, deposit limit, report accounting.
- Violated if: the vault exchange rate is manipulable, stale, fee-on-transfer, or uses nonstandard ERC4626 semantics.

INV-4626-3: `_freeStETH(amount)` should redeem enough vault shares and unwrap all loose wstETH to make at least `amount` stETH available, subject to `vault.maxRedeem`.
- Relied on by: manual swap and Lido withdrawal initiation.
- Violated if: `previewWithdraw` underestimates shares, `maxRedeem` caps redemption, or the function unwraps more wstETH than necessary in a way that changes exposure unexpectedly.

INV-4626-4: `availableDepositLimit` for Strategy4626 must be the minimum of base strategy limit and external vault capacity converted from wstETH to stETH.
- Relied on by: preventing deposits that the vault cannot accept.
- Violated if: vault `maxDeposit` is manipulated or reports a value incompatible with wstETH conversion.

## Factory

INV-FAC-1: There must be at most one factory-recorded Strategy4626 deployment per vault.
- Relied on by: `deployments[vault]` and `isDeployedStrategy`.
- Violated if: reentrancy or constructor side effects allow two strategies for one vault before `deployments[vault]` is written.

INV-FAC-2: New strategies must be initialized with the factory as current management, configured role recipients, pending management set to factory management, performance fee zero, and profit unlock time zero.
- Relied on by: deployer configuration and post-deploy ownership handoff.
- Violated if: any external setter fails, is reentered, or uses stale factory role values.

INV-FAC-3: Only current factory `management` can rotate factory role addresses.
- Relied on by: deployment safety for future strategies.
- Violated if: `management` is set to zero or an unintended address, permanently bricking or redirecting future deployment configuration.

