# Solidity Auditor Lane 9 - Boundary

Scope: commit 521fff28ad978a37115be8995a1d631611fa1d3d, in-scope bundle contracts BaseLSTAccumulator, Strategy, Strategy4626, Strategy4626Factory, StrategyAprOracle.

Result: no FINDING blocks emitted. I found boundary issues worth preserving as LEADs, but each either requires trusted role action, depends on a non-compliant/caller-chosen external vault, or is value-bounded to dust.

## Boundary Work Notes

[Feynman: BaseLSTAccumulator] This is the shared strategy body. It accepts WETH deposits through the inherited Yearn wrapper, optionally turns loose WETH into the liquid staking token, reports WETH plus discounted staking-token value, and only lets ordinary users withdraw whatever WETH is already idle.

[Feynman: BaseLSTAccumulator._depositLimit] This answers "how much more can come in" by subtracting the strategy's currently estimated value from a management-set cap.

[Inversion: BaseLSTAccumulator._depositLimit] Try a cap of zero, a cap of max uint, and an estimated value that reverts before the comparison because reportBuffer is above MAX_BPS.

[Feynman: BaseLSTAccumulator._deployFunds] This is the deposit-time mover. If staking is enabled and the WETH amount is bigger than the dust threshold, it sends that WETH toward the staking route; otherwise it leaves the WETH idle.

[Inversion: BaseLSTAccumulator._deployFunds] Deposit exactly ASSET_DUST, deposit 1 wei, and disable staking before deposit so later report/tend has to decide what to do with idle WETH.

[Feynman: BaseLSTAccumulator._harvestAndReport] This is the report-time accounting path. It refuses to report while Lido queue value is pending, sells rewards if an override exists, stakes loose WETH up to the deposit cap, and returns estimated strategy value to TokenizedStrategy.

[Inversion: BaseLSTAccumulator._harvestAndReport] Leave only 1 wei idle, set reportBuffer above MAX_BPS, and create pendingRedemptions then try to report.

[Feynman: BaseLSTAccumulator.estimatedTotalAssets] This values the strategy as idle WETH plus staking-token value after a basis-point haircut.

[Socratic: BaseLSTAccumulator.estimatedTotalAssets - why?] Why can management set reportBuffer without a MAX_BPS check when the value path subtracts it from MAX_BPS under Solidity checked arithmetic? The implicit belief is that management only supplies basis-point values.

[Feynman: BaseLSTAccumulator._tendTrigger] This tells keepers whether idle WETH is large enough and gas is cheap enough to bother tending.

[Inversion: BaseLSTAccumulator._tendTrigger] Set minAmountToTend to zero, set it to type(uint256).max, and set maxGasPriceToTend to zero on a chain/block with nonzero basefee.

[Feynman: BaseLSTAccumulator.manualSwapToAsset] This lets management convert staking-token value back to WETH, capped to the strategy's current staking-token value.

[Feynman: BaseLSTAccumulator.manualStake] This lets management turn idle WETH into staking-token exposure, capped to idle WETH.

[Feynman: BaseLSTAccumulator.initiateLSTWithdrawal] This lets management move staking-token value into the Lido withdrawal queue and records that the queued amount must be resolved before reports continue.

[Inversion: BaseLSTAccumulator.initiateLSTWithdrawal] Request zero, request more than valueOfLST, and request an amount larger than a single Lido queue request can accept.

[Feynman: BaseLSTAccumulator.claimLSTWithdrawal] This lets keepers claim one completed queue request from caller-supplied bytes and reduces the pending amount by the ETH actually received.

[Inversion: BaseLSTAccumulator.claimLSTWithdrawal] Pass empty bytes, pass the raw returnData from initiateLSTWithdrawal, and pass a valid but unrelated request id that the strategy cannot claim.

[Feynman: Strategy] This is the stETH-specific implementation. It chooses between Curve and Lido for WETH-to-stETH, swaps stETH back through Curve for manual liquidity, and talks to Lido's withdrawal queue.

[Feynman: Strategy.receive] This accepts ETH so Curve and Lido queue claims can deliver native ETH before the strategy wraps it back to WETH.

[Inversion: Strategy.receive] Send ETH directly before a claim, force ETH into the contract, and trigger a swap that wraps the whole ETH balance rather than only the current swap output.

[Feynman: Strategy._stake] This unwraps WETH into ETH, checks whether Curve gives more stETH than direct staking, and otherwise submits ETH to Lido.

[Inversion: Strategy._stake] Stake zero, stake 1 wei, and use a Curve quote that is barely above the input while the downstream vault cap is tight.

[Feynman: Strategy._swapLSTToAsset] This approves stETH to Curve, sells stETH for ETH with a caller-provided minimum output, and wraps all ETH held by the strategy into WETH.

[Feynman: Strategy._initiateLSTWithdrawal] This approves stETH to the Lido queue, asks for one withdrawal request, and returns the encoded request-id array.

[Socratic: Strategy._initiateLSTWithdrawal - why?] Why return an encoded uint256[] when the keeper claim path decodes a single uint256? The implicit belief is that off-chain operators will decode the array and re-encode the chosen request id.

[Feynman: Strategy._claimLSTWithdrawal] This decodes one request id from bytes, claims it from the Lido queue, measures the ETH received, and wraps the whole native ETH balance into WETH.

[Feynman: Strategy.manualClaimWithdrawals] This is an emergency batch claim path for Lido withdrawals, with an option to zero all pending queue accounting.

[Feynman: Strategy4626] This extension adds a downstream wstETH ERC4626 vault. It wraps stETH to wstETH, deposits into the vault, values vault shares, and can redeem/unwrap vault exposure before swaps or queueing.

[Feynman: Strategy4626.constructor] This checks that the chosen vault reports wstETH as its asset, stores that vault, and gives wstETH/stETH approvals needed for operation.

[Inversion: Strategy4626.constructor] Use an address with no code, use a vault that returns wstETH from asset() but is non-compliant elsewhere, and use a vault whose symbol()/asset() behavior reverts.

[Feynman: Strategy4626._stake] This first gets stETH through the parent staking route, wraps all stETH into wstETH, then deposits all wstETH into the downstream vault.

[Socratic: Strategy4626._stake - why?] Why deposit the full resulting wstETH balance instead of min(balance, vault.maxDeposit(address(this)))? The implicit belief is that the pre-deposit capacity check and the staking route output stay aligned.

[Feynman: Strategy4626._swapLSTToAsset] This frees enough stETH from loose wstETH or vault shares, then swaps whatever stETH is available back to WETH.

[Feynman: Strategy4626._initiateLSTWithdrawal] This frees enough stETH from the wrapped/vault position and requires the full requested amount before asking Lido for a queue request.

[Feynman: Strategy4626.availableDepositLimit] This combines the strategy deposit cap with the downstream vault's max wstETH deposit capacity, converted into stETH terms.

[Inversion: Strategy4626.availableDepositLimit] Make maxDeposit zero, make it type(uint256).max, and make it tight while Curve gives a positive stETH premium.

[Feynman: Strategy4626.valueOfWstETH] This values loose wstETH plus vault shares converted back into wstETH, then into stETH.

[Feynman: Strategy4626._freeStETH] This redeems enough vault shares to obtain needed wstETH, adds a two-wei rounding buffer, and unwraps all loose wstETH into stETH.

[Inversion: Strategy4626._freeStETH] Set maxRedeem to zero, make previewWithdraw larger than maxRedeem, and leave a tiny loose wstETH balance so the function unwraps more than strictly needed.

[Feynman: Strategy4626.manualRedeem] This lets emergency authority redeem vault shares into loose wstETH, capped at current vault-share balance.

[Feynman: Strategy4626.manualUnwrap] This lets emergency authority unwrap loose wstETH into stETH, capped at current loose wstETH.

[Feynman: Strategy4626Factory] This deploys one Strategy4626 per chosen vault and stamps the factory's current role addresses onto the new strategy.

[Feynman: Strategy4626Factory.newStrategy4626] This lets anyone ask the factory to deploy a strategy for a vault that has not been used before.

[Inversion: Strategy4626Factory.newStrategy4626] Deploy for a malicious wstETH-looking vault, front-run deployment for a legitimate vault, and use a vault whose ERC20 symbol call is hostile.

[Feynman: Strategy4626Factory.setAddresses] This lets the current factory management rotate the role addresses used for future deployments.

[Feynman: Strategy4626Factory.isDeployedStrategy] This checks whether a strategy is the factory-recorded deployment for the vault that the strategy reports.

[Feynman: StrategyAprOracle] This is a fixed illustrative APR oracle returning 4% regardless of strategy or debt delta.

## Leads

LEAD | contract: BaseLSTAccumulator | function: setReportBuffer/estimatedTotalAssets | bug_class: unbounded-bps-config | group_key: BaseLSTAccumulator | setReportBuffer | unbounded-bps-config
boundary: management-supplied reportBuffer crossing the MAX_BPS arithmetic boundary in estimatedTotalAssets()
assumption: reportBuffer is always a basis-point haircut in the inclusive range 0..MAX_BPS
actual: setReportBuffer stores any uint256; estimatedTotalAssets later evaluates MAX_BPS - reportBuffer under checked arithmetic
code_smells: reportBuffer > 10_000 makes estimatedTotalAssets revert; reportBuffer == 10_000 values all LST/wstETH exposure at zero; the setter has no upper bound while the read path is used by availableDepositLimit() and report()
description: A trusted management misconfiguration can brick deposits/reports or force a full LST valuation haircut, but this is role-only configuration rather than an untrusted exploit path.

LEAD | contract: BaseLSTAccumulator | function: _harvestAndReport/_tend | bug_class: dust-staking-bypasses-deposit-dust-guard | group_key: BaseLSTAccumulator | _harvestAndReport | dust-staking-bypasses-deposit-dust-guard
boundary: idle WETH dust left by _deployFunds() at <= ASSET_DUST and later passed directly into _stake() from report/tend
assumption: the ASSET_DUST guard prevents uneconomic tiny stakes from reaching the Lido/Curve boundary
actual: _deployFunds() has the dust guard, but _harvestAndReport() calls _stake(min(balanceOfAsset(), availableDepositLimit(address(this)))) and _tend() calls _stake(_totalIdle) with no ASSET_DUST check
code_smells: a 1 wei deposit can remain idle at deposit time, then a later report can send that 1 wei through Strategy._stake(); live stETH eth_call evidence at the review date returned getSharesByPooledEth(1) = 0 and submit(1 wei) = 0, so the dust can be donated/lost instead of converted into stETH
description: The dust guard is not consistently applied across deposit/report/tend staking paths, but the demonstrated impact is dust-scale loss/griefing rather than a material exploit.

LEAD | contract: Strategy | function: _initiateLSTWithdrawal/claimLSTWithdrawal | bug_class: queue-claim-data-shape-mismatch | group_key: Strategy | _initiateLSTWithdrawal | queue-claim-data-shape-mismatch
boundary: bytes returnData from initiateLSTWithdrawal() versus bytes _claimData consumed by claimLSTWithdrawal()
assumption: operators understand that initiation returns abi.encode(uint256[]) and claim expects abi.encode(uint256)
actual: _initiateLSTWithdrawal() returns abi.encode(requestIds) for a uint256[] array, while _claimLSTWithdrawal() decodes _claimData as a single uint256 request id
code_smells: direct pass-through of initiation returnData to claimLSTWithdrawal is the wrong ABI shape; in-repo tests explicitly decode the array first and re-encode requestIds[0], which confirms the manual off-chain transformation requirement
description: Queue claim data is easy to supply in the wrong shape and can keep pendingRedemptions unresolved until corrected, but a bad keeper payload reverts/claims the wrong id rather than giving an untrusted party a fund-moving path.

LEAD | contract: Strategy4626 | function: _stake/availableDepositLimit | bug_class: external-vault-capacity-drift | group_key: Strategy4626 | _stake | external-vault-capacity-drift
boundary: downstream ERC4626 vault maxDeposit/preview behavior and Curve/Lido staking output
assumption: the amount admitted by availableDepositLimit() will still be depositable after WETH is converted into stETH and then wstETH
actual: availableDepositLimit() converts vault.maxDeposit(address(this)) from wstETH capacity into stETH terms before execution, but _stake() later deposits the entire resulting wstETH balance without re-capping to the live vault maxDeposit; a Curve route that returns more than 1:1 stETH or a vault cap change can make vault.deposit(wstETHBalance, address(this)) revert
code_smells: the strategy relies on an external vault's live capacity and conversion behavior at two different moments, and the execution path uses the full produced wstETH balance rather than min(wstETHBalance, vault.maxDeposit(address(this)))
description: Tight downstream ERC4626 caps can make otherwise admitted deposits/reports/tends revert at the final vault.deposit boundary, but the immediate effect is a reverted operation rather than loss of already-accounted user funds.

LEAD | contract: Strategy4626Factory | function: newStrategy4626 | bug_class: permissionless-external-vault-trust-boundary | group_key: Strategy4626Factory | newStrategy4626 | permissionless-external-vault-trust-boundary
boundary: caller-supplied _vault address used for ERC20 symbol(), IERC4626 asset(), Strategy4626 approvals, deposits, redemptions, and valuation
assumption: checking vault.asset() == wstETH is sufficient to treat the vault as a safe ERC4626 accounting boundary for strategy users
actual: any caller can deploy a factory-recognized strategy for any contract that reports wstETH as asset(), while later Strategy4626 logic trusts that vault's maxDeposit(), deposit(), convertToAssets(), previewWithdraw(), maxRedeem(), and redeem() behavior
code_smells: deployments[_vault] and isDeployedStrategy() can mark a strategy as factory-created even if the downstream vault is non-compliant or hostile; this is an external trust-boundary issue rather than a direct break against an existing trusted vault
description: The factory creates official-looking strategies for arbitrary wstETH ERC4626 boundaries, so integrators need vault allowlisting or clear trust labeling before treating factory deployment as endorsement.
