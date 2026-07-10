[Feynman: BaseLSTAccumulator] This contract is the common accounting and operations layer. It accepts WETH as the strategy asset, usually turns that WETH into stETH exposure, reports idle WETH plus discounted LST value as strategy value, and keeps a separate counter for Lido withdrawals that have been requested but not claimed.

[Feynman: _depositLimit] This function answers "how much more WETH may enter?" by looking at the strategy's current estimated assets and subtracting that from the configured cap. The fuzzy assumption is that every economically owned asset is visible in `estimatedTotalAssets()` at the moment the cap is checked.

[Inversion: _depositLimit] 1. Move LST into the Lido queue so it is still economically owned but no longer in `balanceOfLST()`, then ask for the cap. 2. Add a positive `reportBuffer` so existing LST is discounted and cap room opens. 3. Create a Curve route that returns more stETH than the WETH input so post-deploy value is larger than the checked deposit amount.

[Feynman: availableDepositLimit] This function decides whether the receiver is allowed to deposit and, if so, forwards the answer from the cap calculation. It does not look at queued withdrawals or any in-flight state other than current balances.

[Feynman: availableWithdrawLimit] This function promises only the WETH already sitting in the strategy for normal exits. It intentionally does not count stETH, wstETH, vault shares, or queued Lido withdrawals.

[Inversion: availableWithdrawLimit] 1. Try to withdraw immediately after all WETH has been staked and expect zero liquid exit capacity. 2. Manually free LST to WETH and confirm the exit limit rises only by idle WETH. 3. Queue LST through Lido and confirm the exit limit does not count pending ETH until it is claimed and wrapped.

[Feynman: _harvestAndReport] This function refuses to report while a Lido withdrawal is pending, sells rewards if any, stakes idle WETH subject to the deposit cap, then returns the estimated total value. Its safety depends on the pending-redemption guard matching every path that removes value from the normal balance view.

[Inversion: _harvestAndReport] 1. Leave `pendingRedemptions > 0` and verify reports cannot update the stale TokenizedStrategy total. 2. Clear pending manually before value has actually returned and force the next report to realize loss. 3. Make the deposit cap undercount value and let the report stake idle WETH into an already-over-cap strategy.

[Feynman: initiateLSTWithdrawal] This management function picks an available LST amount, records it as pending, and asks the child strategy to move that LST into the withdrawal queue. The fuzzy point is that the pending counter represents economic value that later balance-based views do not include.

[Socratic: BaseLSTAccumulator.initiateLSTWithdrawal -- why?] Why does the cap logic ignore `pendingRedemptions` when this function explicitly says the strategy still has an in-flight claim on that value?

[Feynman: claimLSTWithdrawal] This keeper or management function claims a queued withdrawal, wraps received ETH into WETH, and reduces the pending counter by the amount of ETH received. It assumes the caller supplies claim data in the exact shape the child strategy expects.

[Feynman: Strategy] This contract gives the base accumulator its stETH-specific routes: stake WETH through Curve when Curve is better than one-for-one, otherwise stake through Lido, swap stETH back through Curve, and request or claim Lido withdrawal-queue entries.

[Feynman: Strategy._stake] This function turns WETH into ETH, chooses Curve if it quotes more stETH than the input amount, otherwise sends ETH to Lido, and leaves the resulting stETH in the strategy. The important invariant edge is that the amount checked by deposit limits is the WETH input, while the amount received can be larger.

[Inversion: Strategy._stake] 1. Make Curve quote input plus premium so a deposit mints more LST value than the checked WETH amount. 2. Make Curve quote exactly the input and force the Lido branch. 3. Make Curve quote better than one-for-one but return only the minimum and check whether downstream capacity assumed the quote or the actual balance.

[Feynman: Strategy._initiateLSTWithdrawal] This function approves the Lido queue, builds a one-element amount array, requests a withdrawal for the strategy, and returns the request ids encoded as an array.

[Feynman: Strategy._claimLSTWithdrawal] This function expects the claim data to be one request id, asks Lido to claim that id, measures new ETH received, then wraps all ETH sitting on the strategy into WETH.

[Socratic: Strategy._claimLSTWithdrawal -- why?] Why does the claim path decode one `uint256` when the initiate path returns `abi.encode(uint256[] requestIds)`?

[Feynman: Strategy4626] This extension takes stETH exposure one step further: after staking, it wraps stETH into wstETH and deposits the wstETH into an external ERC4626 vault whose asset must be wstETH.

[Feynman: Strategy4626.availableDepositLimit] This function starts with the base strategy deposit room, asks the downstream vault how much wstETH it can accept, converts that wstETH capacity into stETH value, and returns the smaller cap.

[Inversion: Strategy4626.availableDepositLimit] 1. Let Curve produce more stETH than the WETH input so the downstream vault sees more wstETH than this view predicted. 2. Let the downstream vault reduce `maxDeposit` between the view check and the actual `deposit`. 3. Use a vault whose conversion functions round differently from wstETH wrapping at the one-wei boundary.

[Feynman: Strategy4626._freeStETH] This function tries to make enough loose stETH available by using existing stETH first, then loose wstETH, then redeeming downstream vault shares if needed, and finally unwrapping the loose wstETH. The boundary is whether the vault can actually release enough wstETH to satisfy the requested stETH amount.

[Feynman: Strategy4626Factory] This contract stamps new Strategy4626 instances with current role defaults and records one deployment per downstream vault.

[Feynman: Strategy4626Factory.newStrategy4626] This public function checks whether a vault already has a strategy, reads the vault symbol to build a name, deploys the strategy, configures its roles and fees, emits an event, and only then records the vault-to-strategy mapping.

[Socratic: Strategy4626Factory.newStrategy4626 -- why?] Why is the one-shot deployment state written after external calls to the user-supplied vault have already happened?

[Inversion: Strategy4626Factory.newStrategy4626] 1. Make the vault's `symbol()` reenter `newStrategy4626` before `deployments[vault]` is written. 2. Make the vault's `asset()` reenter from the Strategy4626 constructor before the outer call records the deployment. 3. Let the inner call record one strategy and the outer call overwrite the mapping with another.

FINDING | contract: BaseLSTAccumulator | function: availableDepositLimit | bug_class: pending-redemption-cap-bypass | group_key: BaseLSTAccumulator | availableDepositLimit | pending-redemption-cap-bypass
path: management -> `initiateLSTWithdrawal(amount)` moves LST into the Lido queue and increments `pendingRedemptions` -> `estimatedTotalAssets()` no longer counts the queued value -> permissionless depositor calls TokenizedStrategy `deposit()` while `openDeposits` is true -> `_maxDeposit()` accepts the newly opened cap room -> later `claimLSTWithdrawal()` returns the queued WETH and the strategy is over the configured deposit cap
invariant: The configured `depositLimit` should bound strategy economic exposure, including LST value that is temporarily in the withdrawal queue and represented by `pendingRedemptions`.
violation_path: Start with a strategy at its cap, queue part of the LST position, deposit into the artificial room created by excluding queued value, then claim the queued value back.
proof: With `reportBuffer = 0`, `depositLimit = 100 WETH`, and the strategy holding `100 stETH`, `_depositLimit()` returns zero. Management calls `initiateLSTWithdrawal(60)`, which sets `pendingRedemptions = 60` and transfers `60 stETH` to the queue, leaving only `40 stETH` visible to `estimatedTotalAssets()`. `_depositLimit()` now returns `100 - 40 = 60`, so an open depositor can deposit `60 WETH`; TokenizedStrategy only checks `assets <= _maxDeposit()` and then adds `60` to tracked total assets while the strategy stakes the WETH. When the queued request is claimed, the strategy has `60 WETH` from the claim plus `100 stETH` exposure, so `estimatedTotalAssets()` is `160` against a `100` cap.
description: Queued redemptions are treated as pending for reports but omitted from deposit-cap accounting, allowing deposits to exceed the configured capacity during a normal Lido withdrawal lifecycle.
fix: Include `pendingRedemptions` in the cap-side asset estimate or return zero deposit room while `pendingRedemptions != 0`.

FINDING | contract: Strategy4626Factory | function: newStrategy4626 | bug_class: reentrant-deployment-duplicate | group_key: Strategy4626Factory | newStrategy4626 | reentrant-deployment-duplicate
path: attacker -> `newStrategy4626(maliciousVault)` -> malicious vault reenters from `symbol()` or `asset()` before `deployments[maliciousVault]` is written -> inner deployment succeeds -> outer deployment resumes and succeeds -> mapping points to only the outer strategy while both strategies exist
invariant: A vault should have at most one factory-created Strategy4626 deployment, and `deployments[vault]` should be the single source of truth for that deployment.
violation_path: Reenter `newStrategy4626` from a user-supplied vault callback before the first call reaches `deployments[_vault] = address(newStrategy)`.
proof: Let `deployments[V] == address(0)` and let `V.symbol()` reenter the factory once. The outer call passes the initial zero check, calls `ERC20(V).symbol()`, and the reentrant inner call also sees `deployments[V] == address(0)`. The inner call deploys `S1` and sets `deployments[V] = S1`; the outer call then resumes, deploys `S2`, emits another `NewStrategy4626`, and overwrites `deployments[V] = S2`. Final state: `S1` and `S2` are both live strategies configured with factory role defaults, but `isDeployedStrategy(S1)` returns false because the mapping now points to `S2`.
description: The factory's one-shot mapping is written after external callbacks to the user-chosen vault, so a reentrant vault can create duplicate strategies for the same vault.
fix: Reserve the vault with an in-progress sentinel or use a reentrancy guard before any external call to `_vault`, then replace the sentinel with the deployed strategy address after setup completes.

LEAD | contract: Strategy | function: _initiateLSTWithdrawal/_claimLSTWithdrawal | bug_class: claim-data-shape-mismatch | group_key: Strategy | _claimLSTWithdrawal | claim-data-shape-mismatch
code_smells: `_initiateLSTWithdrawal()` returns `abi.encode(requestIds)` where `requestIds` is a `uint256[]`, but `_claimLSTWithdrawal()` decodes `_claimData` as a single `uint256`. Passing the returned bytes directly to `claimLSTWithdrawal()` decodes the ABI offset word (`0x20`) as the request id rather than the actual id. The tests decode the returned array and re-encode `requestIds[0]`, so safe operation is possible but requires an undocumented off-chain shape conversion.
description: The initiate and claim functions do not round-trip the same `bytes` payload, which can strand `pendingRedemptions` for operators that treat the returned `returnData` as later claim data.

LEAD | contract: Strategy4626 | function: availableDepositLimit/_stake | bug_class: max-deposit-view-write-divergence | group_key: Strategy4626 | availableDepositLimit | max-deposit-view-write-divergence
code_smells: `availableDepositLimit()` converts the downstream vault's `maxDeposit(address(this))` from wstETH capacity into a WETH/stETH input cap, but `_stake()` can route through Curve when `get_dy()` is greater than the WETH input and then deposits the entire resulting wrapped balance into the vault. If the downstream vault can accept exactly `100 wstETH` and Curve turns the accepted WETH input into `100 wstETH + premium`, TokenizedStrategy's max-deposit check can pass while `vault.deposit(wstETHBalance)` reverts or requires less than the advertised `availableDepositLimit()`.
description: The max-deposit view assumes deposited WETH maps to no more than that much wrapped vault asset, but the write path intentionally chooses routes that may mint extra stETH before depositing into the downstream vault.
