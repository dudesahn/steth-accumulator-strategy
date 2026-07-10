# Expert 2 Analysis - stETH Accumulator Strategy

## Scope and Methods

Audit lane: Secondary Smart Contract Auditor, independent economic and integration review.

Target scope reviewed as production code:
- `src/BaseLSTAccumulator.sol`
- `src/Strategy.sol`
- `src/Strategy4626.sol`
- `src/Strategy4626Factory.sol`
- `src/periphery/StrategyAprOracle.sol`
- `src/interfaces/*.sol`

Explicitly excluded as target code: `src/test/**`, `.audit`, `.context`, `x-ray`, generated artifacts, cache/broadcast outputs, prior reports, notes, and previous findings. Tests, `foundry.toml`, README, and dependencies were used only as supporting behavior context.

Workflow files read before review:
- `/Users/dudesahn/Documents/GitHub/codex/skill-research/dot-context/skills/smart-contract-audit/SKILL.md`
- `/Users/dudesahn/Documents/GitHub/codex/skill-research/dot-context/skills/smart-contract-audit/multi-expert.md`
- `/Users/dudesahn/Documents/GitHub/codex/skill-research/dot-context/skills/smart-contract-audit/solidity-checks.md`
- `/Users/dudesahn/Documents/GitHub/codex/skill-research/dot-context/skills/smart-contract-audit/finding-format.md`
- `/Users/dudesahn/Documents/GitHub/codex/skill-research/dot-context/skills/smart-contract-audit/reference/solidity/protocols/yield.md`

Methods used:
- Mapped fund flow from WETH deposit to stETH, wstETH, ERC4626 vault shares, Curve exit, and Lido withdrawal queue.
- Reviewed Yearn TokenizedStrategy accounting callbacks as supporting context for deposit, withdraw, report, tend, shutdown, and emergency withdraw behavior.
- Searched target source for external calls, approvals, Curve/Lido/wstETH/ERC4626 calls, ABI encode/decode, role-gated functions, loops, timestamp/basefee usage, and balance-based accounting.
- Ran fork sanity tests with explicit mainnet fork:
  - `forge test --fork-url https://ethereum.publicnode.com --match-path src/test/WithdrawalQueue.t.sol -vv` -> 7 passed
  - `forge test --fork-url https://ethereum.publicnode.com --match-path src/test/Strategy4626.t.sol -vv` -> 5 passed
  - `forge test --fork-url https://ethereum.publicnode.com --match-path src/test/Shutdown.t.sol -vv` -> 3 passed
  - `forge test --fork-url https://ethereum.publicnode.com --match-path src/test/Strategy4626Factory.t.sol -vv` -> 5 passed

Protocol context: Ethereum/Solidity yield strategy, Yearn V3 TokenizedStrategy, WETH asset, stETH LST, Curve ETH/stETH pool, Lido withdrawal queue, optional wstETH ERC4626 vault integration.

## Candidate Findings

### [M-1] Strategy4626 emergency withdraw does not free the normal vault-held position

Severity: Medium

Confidence: High

Locations:
- `src/BaseLSTAccumulator.sol:158-163`
- `src/Strategy4626.sol:29-42`
- `src/Strategy4626.sol:69-75`
- `src/Strategy4626.sol:103-115`
- `src/BaseLSTAccumulator.sol:133-144`

Description:
`BaseLSTAccumulator._emergencyWithdraw()` only checks the raw stETH balance via `balanceOfLST()` and returns immediately when that balance is zero. In the ERC4626 variant, the normal `_stake()` path wraps stETH into wstETH and deposits the wstETH into `vault`, so the strategy's value is usually represented by ERC4626 shares rather than raw stETH. `Strategy4626.valueOfLST()` correctly counts raw stETH plus wstETH/vault value for reporting, but the inherited emergency withdraw path does not use that accounting surface.

Attack path:
1. Users deposit WETH into `Strategy4626`.
2. `_stake()` converts WETH to stETH, wraps to wstETH, and deposits wstETH into the configured ERC4626 vault.
3. An emergency occurs and the emergency admin shuts down the strategy, then calls `emergencyWithdraw(type(uint256).max)`.
4. `BaseLSTAccumulator._emergencyWithdraw()` sees `balanceOfLST() == 0` and returns without redeeming vault shares or producing WETH.
5. Users still cannot redeem because `availableWithdrawLimit()` only exposes liquid WETH.

Economic feasibility:
This is not a permissionless theft path. The economic risk appears during emergency operations: if the ERC4626 vault is paused, compromised, losing value, or if stETH liquidity is deteriorating, the one-call Yearn emergency path fails to free the actual deployed position. Funds are recoverable only through a manual sequence (`manualRedeem`, `manualUnwrap`, then emergency swap), which increases response time and operator error risk during the exact window where delay is expensive.

Practical verification strategy:
Add a fork test for `Strategy4626`: deposit WETH, assert `vault.balanceOf(address(strategy4626)) > 0` and raw stETH is zero, call `shutdownStrategy()`, then call `emergencyWithdraw(type(uint256).max)`. The current expected result is that vault shares and WETH balance do not materially change. Then perform `manualRedeem`, `manualUnwrap`, and `emergencyWithdraw` to show the manual workaround.

Recommendation:
Override `_emergencyWithdraw()` in `Strategy4626` so it frees from the ERC4626 vault and wstETH before swapping stETH to WETH. The amount cap should use `valueOfLST()` or an ERC4626-aware helper rather than raw `balanceOfLST()`. Also add dedicated shutdown tests for `Strategy4626`, not only the base `Strategy`.

### [M-2] Manual LST-to-WETH liquidity can be withdrawn against stale pre-swap accounting

Severity: Medium

Confidence: Medium

Locations:
- `src/BaseLSTAccumulator.sol:133-155`
- `src/BaseLSTAccumulator.sol:177-179`
- `src/BaseLSTAccumulator.sol:241-246`
- `src/Strategy.sol:74-81`
- Supporting Yearn context: `lib/tokenized-strategy/src/TokenizedStrategy.sol:895-926`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:989-1044`
- Supporting health-check context: `lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol:35-36`, `lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol:136-158`

Description:
The strategy values stETH and ERC4626-held wstETH at nominal stETH value in `estimatedTotalAssets()`, optionally reduced by `reportBuffer`. When management calls `manualSwapToAsset()`, Curve can realize a lower WETH amount than the current Yearn `totalAssets` value, especially during a stETH discount, Curve imbalance, or emergency exit. The WETH produced by the manual swap is immediately exposed by `availableWithdrawLimit()`, but Yearn accounting is not updated until a later `report()`.

This creates a first-withdrawer advantage. Between the manual swap and the loss-recording report, users can redeem liquid WETH at the old PPS. Early redeemers avoid the realized Curve/stETH loss while later holders absorb it.

Attack path:
1. Strategy shares are backed by stETH or vault-held wstETH valued near 1:1 in the last report.
2. stETH trades at a discount or an external ERC4626 vault position loses value.
3. Management calls `manualSwapToAsset(amount, minOut)` to create WETH liquidity, potentially with a permissive `_minOut`.
4. Before a report records the lower asset value, a share holder redeems against the newly liquid WETH.
5. The user exits at stale PPS; the remaining share holders inherit the unreported loss.

Economic feasibility:
The attacker does not need to manipulate Curve if a real discount or emergency unwind already exists; the profit is avoided loss. The exploitable window is created by an observable management transaction that creates WETH liquidity without atomically updating Yearn accounting. A searcher or large holder can backrun the swap transaction and redeem before keepers perform a loss report. The health check default loss limit can also make an immediate loss report revert unless management deliberately disables it, extending the operational window.

Practical verification strategy:
Use a harness or mocked Curve exit that returns 90 WETH for 100 stETH. Deposit two users into the strategy, manually swap the stETH at the mocked discount, and let one user redeem before any report. Verify that the early redeemer receives WETH using the stale pre-loss PPS and that the remaining user's post-report claim absorbs more than their pro-rata share of the loss. Also test the operational mitigation: disabling deposits/restaking and reporting the realized loss before any user withdrawal.

Recommendation:
Do not expose manually created WETH as withdrawable liquidity until the realized loss has been accounted for. Practical fixes include setting a `liquidityPendingReport` flag in manual/emergency swap paths that makes `availableWithdrawLimit()` return zero until a report, adding an atomic management function that swaps and records accounting in one operation, and ensuring report logic does not re-stake emergency liquidity. Operationally, use private/bundled transactions and set conservative `_minOut` values.

### [L-1] Lido withdrawal initiation returns an encoded array but keeper claim decodes a scalar request id

Severity: Low

Confidence: High

Locations:
- `src/Strategy.sol:91-99`
- `src/Strategy.sol:104-112`
- `src/BaseLSTAccumulator.sol:146-147`
- `src/BaseLSTAccumulator.sol:259-272`

Description:
`_initiateLSTWithdrawal()` calls Lido's queue with a one-element amount array and returns `abi.encode(requestIds)`, where `requestIds` is `uint256[]`. `_claimLSTWithdrawal()` decodes the supplied bytes as a single `uint256`. The existing test suite works around this by decoding the returned array and re-encoding `requestIds[0]` before calling `claimLSTWithdrawal`, which confirms the integration expectation is not self-consistent.

Attack path:
1. Management initiates a Lido withdrawal and receives the returned `bytes`.
2. Keeper automation treats that return value as the claim payload and passes it to `claimLSTWithdrawal`.
3. The claim path decodes the ABI array payload as a scalar request id, producing the wrong id or reverting at the queue.
4. `pendingRedemptions` remains non-zero, causing future reports to revert with `Pending redemptions`.

Economic feasibility:
This is primarily an automation and integration DoS, not a direct theft vector. It can delay reporting, profit realization, and withdrawal operations until operators manually decode/re-encode the request id or use the emergency batch claim path. The cost is operational delay and potentially stale accounting during Lido withdrawal periods.

Practical verification strategy:
Add a test that calls `bytes memory data = initiateLSTWithdrawal(amount)` and then directly calls `claimLSTWithdrawal(data)`. The current behavior should fail or claim the wrong request id. Then show that `claimLSTWithdrawal(abi.encode(requestIds[0]))` succeeds.

Recommendation:
Make the ABI contract self-consistent. Either return `abi.encode(requestIds[0])` when only one request is supported, or decode `uint256[]` in the claim path and claim all ids or the first id explicitly. Update interface comments and keeper documentation to match the chosen payload.

### [L-2] APR oracle returns a fixed 4 percent APR for every strategy and debt delta

Severity: Low

Confidence: High

Locations:
- `src/periphery/StrategyAprOracle.sol:28-32`

Description:
`StrategyAprOracle.aprAfterDebtChange()` ignores `_strategy` and `_delta` and always returns `4e16`. If this periphery contract is wired into a Yearn allocator or any debt-management process as a production oracle, it can overstate APR for shutdown, capped, paused, full, depegged, or negative-yield strategies and understate APR for stronger opportunities.

Attack path:
1. An allocator integrates the oracle for strategy debt decisions.
2. The target strategy's real marginal APR diverges from 4 percent, or the strategy has no available capacity.
3. The allocator still sees a fixed positive APR and may allocate debt into a non-optimal or impaired strategy.
4. Users bear opportunity cost or losses from misallocation.

Economic feasibility:
There is no clear direct adversarial extraction path from this oracle alone. The risk is integration-driven capital misallocation if the example oracle is deployed or trusted in production. The downside grows with allocator authority and TVL routed through the oracle.

Practical verification strategy:
Call `aprAfterDebtChange()` with different strategy addresses, a shutdown strategy, and large positive/negative `_delta` values. The function returns the same `4e16` in all cases. Then compare to a real APR model using Lido share-rate growth, ERC4626 vault `totalAssets/totalSupply`, and capacity limits.

Recommendation:
Do not deploy the constant oracle as production infrastructure. Validate `_strategy`, return zero for shutdown/paused/capacity-zero states, incorporate `_delta` into marginal APR, and calculate APR from real stETH/wstETH/vault state or a bounded external oracle.

## Dismissed and False-Positive Notes

- First-depositor/share-inflation against the Yearn strategy itself was not confirmed. TokenizedStrategy tracks `totalAssets` internally rather than using raw asset donations as accounting, and deposits to the strategy address itself are blocked in the Yearn implementation. External ERC4626 vault inflation remains an integration risk for selected vaults, not a bug in this strategy's share math.
- Reentrancy was not confirmed. User-facing Yearn paths are protected by TokenizedStrategy's `nonReentrant`, and the concrete token set is WETH/stETH/wstETH rather than hook-based arbitrary tokens. The main callback-like surfaces are Curve/Lido ETH receipts, which are role-gated or occur under Yearn's guarded paths.
- The ETH-to-stETH route in `_stake()` has a minimum of 1:1 when Curve is used and falls back to Lido submit otherwise, so a standard sandwich cannot force less than 1:1 stETH on deposits. The stETH-to-WETH exit is different because management/emergency paths can choose `_minOut == 0`; that risk is captured in M-2.
- Access control on strategy setters and manual operations is routed through Yearn TokenizedStrategy roles and appeared consistent. The factory's `newStrategy4626()` is permissionless, but deployed strategies remain controlled by the factory/pending configured management and deposits are not opened by the factory, so I did not classify this as direct unauthorized control.
- `pendingRedemptions` blocking reports is intentional while Lido withdrawals are outstanding. The concern is the ABI mismatch in L-1, not the existence of the pending-redemption guard.
- Fee-on-transfer and decimal-mismatch concerns are limited by the hard-coded WETH/stETH/wstETH integrations and SafeERC20/forceApprove usage. Arbitrary ERC20 support is not exposed in the strategy contracts reviewed.
- No unbounded production loops over user-controlled storage were found. The batch Lido claim accepts calldata arrays in an emergency-only path, so gas limits are operator-controlled.
- `setReportBuffer()` has no upper bound, and values above `MAX_BPS` would underflow in `estimatedTotalAssets()`. Because this is management-only misconfiguration with direct observability and recovery by setting a sane value, I treated it as an operational hardening note rather than a security finding.

--- END OF EXPERT 2 ANALYSIS ---
