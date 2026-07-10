# Solidity Auditor Lane 1 - Math Precision

Scope: BaseLSTAccumulator, Strategy, Strategy4626, Strategy4626Factory, StrategyAprOracle at commit 521fff28ad978a37115be8995a1d631611fa1d3d.

Result: No confirmed FINDING blocks. The items below are LEADs because they are real math/accounting trails but depend on trusted-role intent or external integration conditions.

## Mental Tool Markers

[Feynman: BaseLSTAccumulator] This base strategy holds WETH, turns WETH into an LST when asked, reports WETH plus discounted LST value, and exposes role-controlled ways to stake, swap back, queue withdrawals, or clear queue accounting.

[Feynman: BaseLSTAccumulator._depositLimit] This computes how much more value the strategy is willing to accept by subtracting the current reported value from a management-set ceiling.

[Inversion: BaseLSTAccumulator._depositLimit] 1. Set a positive report buffer so reported value falls and deposit headroom opens. 2. Donate idle WETH before a report so current value includes loose assets. 3. Push current reported assets above the limit and verify the subtraction clamps to zero.

[Feynman: BaseLSTAccumulator._deployFunds] This takes newly received WETH and stakes it only when staking is enabled and the amount is above the dust threshold.

[Feynman: BaseLSTAccumulator._freeFunds] This leaves withdrawals unfunded by design; normal exits only use WETH already sitting in the strategy.

[Feynman: BaseLSTAccumulator.availableDepositLimit] This lets a depositor in only if deposits are open or that address is allowed, then returns the remaining strategy capacity.

[Feynman: BaseLSTAccumulator.availableWithdrawLimit] This tells the tokenized strategy that users can withdraw only the idle WETH balance, not the staked or queued side.

[Feynman: BaseLSTAccumulator._harvestAndReport] This blocks while a Lido redemption is pending, sells rewards, stakes loose WETH up to capacity, then reports the strategy's discounted total value.

[Inversion: BaseLSTAccumulator._harvestAndReport] 1. Leave pendingRedemptions nonzero and force report to revert. 2. Give the strategy idle WETH when downstream capacity is tight and make the staking subcall revert. 3. Set a report buffer above the basis-point denominator and make the total-value calculation revert.

[Feynman: BaseLSTAccumulator._emergencyWithdraw] This tries to turn at most the requested amount of LST exposure into WETH during shutdown.

[Feynman: BaseLSTAccumulator._tend] This stakes the WETH amount that the tend path passes in.

[Feynman: BaseLSTAccumulator._tendTrigger] This says tending is worthwhile only when idle WETH is above the configured minimum and gas is not above the configured ceiling.

[Feynman: BaseLSTAccumulator.estimatedTotalAssets] This adds idle WETH to LST value after applying a basis-point haircut.

[Socratic: BaseLSTAccumulator.estimatedTotalAssets - why?] Why is reportBuffer subtracted without a bound check? The code assumes management will keep reportBuffer at or below MAX_BPS.

[Feynman: BaseLSTAccumulator.balanceOfAsset] This reads how much WETH the strategy directly holds.

[Feynman: BaseLSTAccumulator.balanceOfLST] This reads how much raw LST the strategy directly holds.

[Feynman: BaseLSTAccumulator.valueOfLST] This default version treats every LST wei as one WETH wei.

[Feynman: BaseLSTAccumulator.setReportBuffer] This lets management pick the LST haircut used by reported value.

[Feynman: BaseLSTAccumulator.setStakeAsset] This lets management turn automatic staking on or off.

[Feynman: BaseLSTAccumulator.setDepositLimit] This lets management set the strategy capacity ceiling.

[Feynman: BaseLSTAccumulator.setOpenDeposits] This lets management decide whether everyone can deposit.

[Feynman: BaseLSTAccumulator.setAllowed] This lets management allow or block a specific depositor when deposits are closed.

[Feynman: BaseLSTAccumulator.setMinAmountToTend] This lets management set the minimum idle WETH that makes tending worthwhile.

[Feynman: BaseLSTAccumulator.setMaxGasPriceToTend] This lets management set the highest basefee where tending should happen.

[Feynman: BaseLSTAccumulator.manualSwapToAsset] This lets management ask the strategy to turn available LST exposure back into WETH with a caller-provided minimum output.

[Feynman: BaseLSTAccumulator.manualStake] This lets management stake available idle WETH.

[Feynman: BaseLSTAccumulator.initiateLSTWithdrawal] This caps a requested withdrawal by reported LST value, records it as pending, then asks the child strategy to open a Lido withdrawal request.

[Feynman: BaseLSTAccumulator.claimLSTWithdrawal] This lets an authorized keeper claim a finished Lido withdrawal and reduces pending accounting by the ETH amount actually received.

[Feynman: BaseLSTAccumulator.clearPendingRedemptions] This lets management manually lower pending redemption accounting so reports can proceed after an emergency decision.

[Feynman: Strategy] This concrete strategy uses WETH as the asset, stETH as the LST, Curve as the optional better-than-1:1 route, and the Lido queue for delayed exits.

[Feynman: Strategy._depositLimit] This blocks new deposits while stETH staking is paused, otherwise it reuses the base capacity math.

[Feynman: Strategy._stake] This turns WETH into ETH, chooses Curve only when Curve quotes more stETH than direct Lido staking, and otherwise submits ETH to Lido.

[Inversion: Strategy._stake] 1. Make Curve quote exactly amount plus a tiny premium and see whether downstream capacity still fits. 2. Make Curve quote below amount and confirm direct Lido staking avoids slippage math. 3. Use a small amount near dust and verify it either stakes or remains idle without zero-share damage.

[Feynman: Strategy._swapLSTToAsset] This approves stETH to Curve, swaps stETH into ETH with the caller's minimum, then wraps all ETH held by the strategy into WETH.

[Feynman: Strategy._initiateLSTWithdrawal] This approves the Lido queue, submits one stETH withdrawal amount, and returns the request id array encoded for the caller.

[Feynman: Strategy._claimLSTWithdrawal] This decodes a request id, claims that Lido withdrawal, measures newly received ETH, and wraps the whole ETH balance into WETH.

[Feynman: Strategy.manualClaimWithdrawals] This emergency path batch-claims Lido withdrawals, optionally zeroes pending accounting, then wraps ETH into WETH.

[Feynman: Strategy.setReferral] This lets management set the Lido referral address.

[Feynman: Strategy4626] This version turns stETH into wstETH and then deposits that wstETH into a downstream ERC4626 vault.

[Feynman: Strategy4626.constructor] This accepts only a vault whose asset is wstETH, then gives approvals for stETH wrapping and vault deposits.

[Feynman: Strategy4626._stake] This performs the normal stETH acquisition, wraps all stETH held by the strategy, and deposits all resulting wstETH into the downstream vault.

[Inversion: Strategy4626._stake] 1. Deposit exactly the advertised capacity while Curve returns more stETH than the input amount. 2. Leave tiny stETH dust that wraps to zero and check whether it can strand value. 3. Use a downstream vault whose maxDeposit changes between the view cap and the actual vault deposit.

[Feynman: Strategy4626._swapLSTToAsset] This first frees enough stETH from wstETH or vault shares, then swaps the available stETH back to WETH.

[Feynman: Strategy4626._initiateLSTWithdrawal] This frees enough stETH, requires the requested stETH to be present, then submits the Lido withdrawal.

[Feynman: Strategy4626.availableDepositLimit] This starts with the base WETH capacity and, if the downstream vault has a finite wstETH deposit cap, maps that wstETH cap back into stETH-denominated WETH capacity.

[Socratic: Strategy4626.availableDepositLimit - why?] Why is vault.maxDeposit converted with getStETHByWstETH before the actual staking route is known? The code assumes the WETH-to-stETH step will not create more wstETH than the cap permits.

[Feynman: Strategy4626.balanceOfWstETH] This reads loose wstETH held directly by the strategy.

[Feynman: Strategy4626.valueOfWstETH] This values loose wstETH plus vault-share assets as stETH.

[Feynman: Strategy4626.valueOfLST] This counts raw stETH plus the stETH value of loose wstETH and downstream vault assets.

[Feynman: Strategy4626._freeStETH] This makes enough raw stETH available by redeeming vault shares if needed, adding two wei of wstETH as a rounding cushion, then unwrapping loose wstETH.

[Socratic: Strategy4626._freeStETH - why?] Why is a fixed two-wei cushion assumed sufficient? For compliant wstETH and ERC4626 rounding it should cover floor/ceil effects, but the proof relies on downstream conversion consistency.

[Feynman: Strategy4626._stETHValue] This converts a wstETH amount into its stETH value, returning zero for zero input.

[Feynman: Strategy4626.manualRedeem] This lets an emergency role redeem downstream vault shares into loose wstETH.

[Feynman: Strategy4626.manualUnwrap] This lets an emergency role unwrap loose wstETH into raw stETH.

[Feynman: Strategy4626Factory] This factory creates one Strategy4626 per vault and stamps each new strategy with the factory's current role defaults.

[Feynman: Strategy4626Factory.newStrategy4626] This deploys a new Strategy4626 for a chosen vault, initializes fee and role settings, records the deployment, and returns the new strategy address.

[Feynman: Strategy4626Factory.setAddresses] This lets the current factory management address rotate the defaults used for future strategy deployments.

[Feynman: Strategy4626Factory.isDeployedStrategy] This checks whether a strategy address is the registered strategy for the vault that strategy reports.

[Feynman: StrategyAprOracle] This periphery oracle gives callers a fixed APR number.

[Feynman: StrategyAprOracle.aprAfterDebtChange] This ignores the strategy and debt change inputs and always returns 4% APR scaled by 1e18.

## Output

LEAD | contract: Strategy4626 | function: availableDepositLimit/_stake | bug_class: capacity-conversion-rounding | group_key: Strategy4626 | availableDepositLimit/_stake | capacity-conversion-rounding
code_smells: `availableDepositLimit` converts `vault.maxDeposit(address(this))` from wstETH capacity into stETH/WETH capacity before the route output is known, while `_stake` later deposits all resulting wstETH into the downstream vault. If Curve returns more stETH than the WETH input, the wrapped amount can exceed the finite vault cap that was used to approve the deposit amount. Concrete arithmetic: with `vault.maxDeposit(this) = 100e18` wstETH and `1 wstETH = 1.2 stETH`, `_stETHValue(maxDeposit)` advertises `120e18` WETH capacity; if Curve returns `120e18 + 2` stETH, wrapping floors to `100e18 + 1` wstETH, so an OpenZeppelin-style ERC4626 vault with unchanged `maxDeposit(this) = 100e18` reverts `deposit(100e18 + 1, this)` as more than max.
description: A finite-cap downstream vault plus a positive Curve stETH premium can make the strategy advertise a WETH deposit/report capacity that later reverts at `vault.deposit`; validate with a finite-cap wstETH ERC4626 harness and consider capping the actual vault deposit or leaving excess wstETH loose.

LEAD | contract: BaseLSTAccumulator | function: setReportBuffer/estimatedTotalAssets | bug_class: basis-point-bound | group_key: BaseLSTAccumulator | setReportBuffer/estimatedTotalAssets | basis-point-bound
code_smells: `setReportBuffer` stores any management-provided value, but `estimatedTotalAssets` computes `MAX_BPS - reportBuffer` under checked arithmetic. Concrete arithmetic: with `MAX_BPS = 10_000` and `reportBuffer = 10_001`, every call to `estimatedTotalAssets` underflows before applying the LST haircut, and report/deposit-limit paths that depend on ETA revert.
description: This is management-only and therefore not a confirmed external exploit under the shared rules, but the basis-point parameter should be clamped to `<= MAX_BPS` if accidental report/deposit-limit DoS is out of scope.

LEAD | contract: StrategyAprOracle | function: aprAfterDebtChange | bug_class: fixed-apr-model | group_key: StrategyAprOracle | aprAfterDebtChange | fixed-apr-model
code_smells: The APR oracle returns `4e16` for every `_strategy` and every `_delta`, so positive debt changes, debt reductions, actual stETH/vault APR, utilization, fees, and capacity constraints have no effect on the 1e18-scaled result.
description: No in-repo value-moving path proves an exploit, but this periphery oracle is a placeholder-quality fixed-rate model and should not be wired into production debt allocation without replacing the constant with strategy-aware math.
