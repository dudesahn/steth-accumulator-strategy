# Agent 4 - Execution Trace Lane

Scope: stETH Accumulator Strategy at 521fff28ad978a37115be8995a1d631611fa1d3d.
Specialty: concrete call traces across deposit, withdraw, report, tend, manual swap/stake, Lido queue request/claim, factory deployment, and external call ordering.

## Working markers

[Feynman: BaseLSTAccumulator] This contract is the shared strategy body. It accepts WETH through the inherited strategy wrapper, decides when loose WETH should be turned into the staking token, reports the strategy's WETH-equivalent value, and exposes role-only manual paths for staking, swapping back, and using the Lido withdrawal queue.

[Feynman: Strategy] This contract is the stETH-specific adapter. It turns WETH into ETH, then either buys stETH from Curve when Curve is better than one-for-one or submits ETH to Lido. It can also sell stETH back through Curve, request a Lido queue withdrawal, and claim completed queue withdrawals into WETH.

[Feynman: Strategy4626] This contract adds a second yield layer. After getting stETH, it wraps the stETH into wstETH and deposits that into an external vault. When it needs stETH again, it pulls wstETH back from loose balance or the vault, unwraps it, then lets the base stETH logic continue.

[Feynman: Strategy4626Factory] This contract lets anyone deploy one Strategy4626 for a chosen vault. The deployed strategy gets the factory's configured role addresses and records the vault-to-strategy mapping.

[Feynman: StrategyAprOracle] This contract always returns the same APR estimate for any strategy and any debt delta.

[Feynman: initiateLSTWithdrawal] Management chooses an amount of LST value to queue. The base contract marks that amount as pending before the strategy frees stETH if needed, approves the queue, asks the queue for a withdrawal request, and returns bytes that are supposed to be used later.

[Feynman: claimLSTWithdrawal] A keeper or management supplies claim bytes. The strategy interprets those bytes as a single request id, asks the queue to pay out that request, wraps the received ETH into WETH, and then the base contract reduces the pending-redemption counter by the amount received.

[Socratic: src/Strategy.sol:104 - why?] Why does the claim side decode a single uint256 when the request side returns abi.encode(requestIds) where requestIds is a uint256 array?

[Inversion: claimLSTWithdrawal] 1. Pass the exact bytes returned by initiateLSTWithdrawal after the queue returns [1]. 2. Pass bytes for a different request id owned by the strategy while an older request remains pending. 3. Pass bytes for a non-existent request id so the queue reverts before pendingRedemptions can decrease.

[Feynman: _deployFunds] At the end of a user deposit, the inherited wrapper gives this strategy the full WETH balance sitting in the strategy, not just the new user's amount. If staking is enabled and that full balance is above dust, this function sends all of it into the stETH path.

[Feynman: _harvestAndReport] A keeper report refuses to run while a Lido withdrawal is marked pending. Otherwise it sells rewards if any, stakes loose WETH up to the deposit limit, and returns the strategy's current WETH plus haircut LST value for accounting.

[Feynman: _tend] A keeper tend call takes the loose WETH amount supplied by the inherited wrapper and sends it into the staking path.

[Inversion: staking callbacks] 1. Leave WETH idle for withdrawals, then make a tiny allowed deposit while stakeAsset is true. 2. Set stakeAsset to false, then call keeper report with idle WETH present. 3. Set stakeAsset to false, then call keeper tend with idle WETH present.

[Feynman: _freeStETH] This helper tries to make enough stETH available by using loose stETH first, then loose wstETH, then redeeming shares from the external vault. After that it unwraps all loose wstETH it sees.

[Socratic: src/Strategy4626.sol:95 - why?] Why unwrap the entire wrappedBalance instead of only the amount needed for the current swap or queue request?

[Inversion: _freeStETH] 1. Make the external vault report value but return maxRedeem as zero. 2. Leave loose wstETH from a manualRedeem and then trigger a small stake. 3. Make vault maxDeposit smaller than loose wstETH plus the next staked amount.

[Feynman: newStrategy4626] Any caller can pick a vault and ask the factory to create a strategy for it. The factory checks only whether that vault already has a deployment, reads the vault symbol for the strategy name, deploys the strategy, stamps configured roles, and records the deployment.

[Inversion: newStrategy4626] 1. Use a vault whose asset function returns wstETH but whose deposit path is hostile. 2. Front-run an expected deployment for a vault, forcing the canonical factory mapping to the same role-stamped strategy. 3. Use a vault with awkward symbol behavior to block deployment.

## Findings and leads

FINDING | contract: Strategy | function: _claimLSTWithdrawal | bug_class: claim-data-abi-mismatch | group_key: Strategy | _claimLSTWithdrawal | claim-data-abi-mismatch
path: management -> initiateLSTWithdrawal(amount) -> Strategy._initiateLSTWithdrawal() returns abi.encode(uint256[] requestIds) -> keeper/management forwards those returned bytes to claimLSTWithdrawal(bytes) -> Strategy._claimLSTWithdrawal() decodes the first word as uint256 -> queue claim targets request id 32 instead of the returned request id -> the intended request stays unclaimed and pendingRedemptions remains nonzero, blocking report().
input: management supplies _amount = 10e18 to initiateLSTWithdrawal; the queue returns requestIds = [1]; keeper/management supplies the exact returned returnData as _claimData to claimLSTWithdrawal.
assumption: the bytes returned by the request function are the claim data accepted by the paired claim function.
proof: _initiateLSTWithdrawal builds a one-element uint256[] and returns abi.encode(requestIds). For requestIds = [1], dynamic-array ABI encoding begins with offset 0x20, then length 1, then element 1. _claimLSTWithdrawal decodes the same bytes as (uint256), so _requestId becomes 32, not 1, and the strategy calls IQueue.claimWithdrawal(32). The base claim wrapper only decreases pendingRedemptions after _claimLSTWithdrawal returns a redeemed amount, while report() requires pendingRedemptions == 0. Therefore the direct request -> returned bytes -> claim trace cannot clear the request that was just enqueued; tests work around this by decoding the returned uint256[] off-chain and passing abi.encode(requestIds[0]) instead of the returned bytes.
description: The request and claim legs use incompatible ABI shapes, so the returned queue data cannot be consumed by the strategy's own claim entry point.
fix: Return abi.encode(requestIds[0]) for the single-request flow, or change _claimLSTWithdrawal to decode uint256[] with a length check and claim the expected element.

LEAD | contract: BaseLSTAccumulator | function: _deployFunds/_harvestAndReport/_tend | bug_class: idle-liquidity-restake-grief | group_key: BaseLSTAccumulator | staking callbacks | idle-liquidity-restake-grief
code_smells: Normal withdrawals are capped to idle WETH, but multiple callbacks can restake idle WETH. The inherited deposit path calls deployFunds(asset.balanceOf(strategy)), so an allowed depositor can trigger _deployFunds on the whole idle balance, not just the new deposit. Separately, _harvestAndReport and _tend call _stake on idle WETH without checking stakeAsset, even if management set stakeAsset to false.
description: If idle WETH was prepared for withdrawals or post-claim liquidity, an allowed depositor or keeper call can move that liquidity back into stETH and make maxWithdraw fall to zero; this is a plausible grief trace but depends on whether operators rely on stakeAsset/openDeposits to preserve idle liquidity.

LEAD | contract: Strategy4626 | function: _swapLSTToAsset/_freeStETH | bug_class: partial-unwind-without-postcondition | group_key: Strategy4626 | _swapLSTToAsset | partial-unwind-without-postcondition
code_smells: Base manualSwapToAsset accepts any amount up to valueOfLST(), and Strategy4626 valueOfLST includes downstream vault assets. _freeStETH only redeems up to vault.maxRedeem(address(this)); _swapLSTToAsset then calls the base swap with Math.min(requested amount, current stETH balance) and has no postcondition that the requested amount was actually freed.
description: A vault-capacity edge such as maxRedeem == 0 can make a manual swap request pass the value check but free and swap less than requested, or possibly call Curve with zero; impact needs confirmation against the intended emergency/liquidity operations.

LEAD | contract: Strategy4626 | function: _stake | bug_class: vault-capacity-overrun-from-loose-balances | group_key: Strategy4626 | _stake | vault-capacity-overrun-from-loose-balances
code_smells: availableDepositLimit caps new deposits using vault.maxDeposit(address(this)), but _stake wraps all loose stETH and then deposits the entire loose wstETH balance into the vault. Loose stETH/wstETH can exist after manualRedeem, manualUnwrap, partial frees, or other maintenance paths, and those balances are not subtracted from the next vault.deposit amount.
description: A deposit/report/tend can attempt to deposit more wstETH than the downstream vault's advertised capacity once loose wrapped balances already exist; this is a capacity/ordering lead because it depends on external vault behavior and prior maintenance state.

LEAD | contract: Strategy4626Factory | function: newStrategy4626 | bug_class: permissionless-vault-trust-stamping | group_key: Strategy4626Factory | newStrategy4626 | permissionless-vault-trust-stamping
code_smells: Any caller can deploy a strategy for any contract whose asset() returns wstETH. The Strategy4626 constructor then grants unlimited wstETH allowance to that vault, and the factory stamps the configured Yearn role addresses before recording the deployment.
description: The factory mapping can contain role-stamped strategies for arbitrary wstETH-denominated vaults, including hostile vault contracts; this is not a direct exploit without operator/user adoption, but the execution trace leaves vault allowlist/trust assumptions off-chain.

## Discarded execution traces

- pendingRedemptions is incremented before the external queue request, but a request revert reverts the increment in the same transaction.
- _swapLSTToAsset and _claimLSTWithdrawal wrap address(this).balance rather than only the received delta; forced ETH becomes WETH held by the strategy and did not produce an attacker-drain trace.
- Factory deployment reads ERC20(_vault).symbol() before deployments[_vault] is set, but the typed symbol call is view/static in this call shape, so I did not keep a state-changing reentrancy finding.
