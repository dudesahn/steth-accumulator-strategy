# Dot-Context Triager Validation

## Triager Posture

Persona: Customer Validation Expert and budget protector. I challenged all Expert 1, Expert 2, Slither, and orchestrator candidates against concrete exploitability, code locations, existing Yearn controls, role assumptions, and fork-test evidence.

## Validated Findings

### M-01 Factory-created Strategy4626 deployments disable profit locking, allowing pre-report deposits to capture prior yield

Status: RELUCTANTLY VALID
Severity: Medium
Confidence: High

Cross-reference analysis:
- Raised by Expert 1.
- Not raised by Expert 2.
- Verified by orchestrator PoC `FactoryProfitUnlockDilutionPoC.t.sol`.
- No contradiction found in TokenizedStrategy: deposits price from last reported `totalAssets`; factory sets `profitMaxUnlockTime` to zero.

Economic feasibility:
- Requires open deposits and unreported profit.
- Profit scales with attacker deposit size and accrued unreported yield.
- Not immediate principal theft, but a same-report-cycle depositor can capture yield earned before their entry.

Technical disproof attempts:
- Checked whether TokenizedStrategy virtual accounting prevents direct donation share inflation. It does prevent raw donation PPS manipulation, but does not prevent deposits from entering before a keeper report recognizes actual strategy profit.
- Checked whether factory-created strategies keep default 10-day unlock. They do not; `Strategy4626Factory.newStrategy4626()` calls `setProfitMaxUnlockTime(0)`.

Validation result:
- The PoC shows an attacker deposits after ERC4626 vault profit accrues but before report, then their shares immediately become worth more after report because profit is unlocked instantly.

### M-02 Manual LST-to-WETH swaps expose discounted liquidity before Yearn accounting records the loss

Status: RELUCTANTLY VALID
Severity: Medium
Confidence: High

Cross-reference analysis:
- Raised by Expert 2.
- Independently verified by orchestrator PoC `ManualSwapStaleAccountingPoC.t.sol`.
- Related to but distinct from shutdown/report redeployment. This issue is about early redeemers avoiding a realized loss between manual liquidity creation and report.

Economic feasibility:
- Requires management to execute a manual swap that realizes a discount or loss.
- Attack is avoided-loss extraction: a holder redeems immediately after liquidity appears and before a report records the lower asset value.
- No need to manipulate Curve if the discount is real; the attacker races an observable liquidity-creation transaction.

Technical disproof attempts:
- Checked whether withdrawals call report or revalue the strategy before transferring idle WETH. They do not.
- Checked whether `availableWithdrawLimit()` blocks the new WETH. It returns `balanceOfAsset()`, exposing the WETH immediately.

Validation result:
- The PoC uses a mocked Curve pool returning about 90% and shows the first redeemer receives more than their pro-rata share of realized liquidity, leaving later holders with the loss.

### M-03 A post-shutdown report can re-stake emergency-withdrawn WETH and block withdrawals again

Status: RELUCTANTLY VALID
Severity: Medium
Confidence: High

Cross-reference analysis:
- Found during orchestrator validation.
- Supported by TokenizedStrategy/BaseStrategy comments warning strategies to avoid redeployment after shutdown.
- Verified by orchestrator PoC `ShutdownReportRedeployPoC.t.sol`.

Economic feasibility:
- Requires the strategy to be shut down and emergency funds to have been freed.
- Trigger requires a keeper/management report after shutdown, so this is not a fully permissionless exploit.
- Impact is a renewed liquidity lock/operational failure during emergency recovery.

Technical disproof attempts:
- Checked whether `_harvestAndReport()` guards `TokenizedStrategy.isShutdown()`. It does not.
- Checked whether `report()` is disabled after shutdown. It is intentionally still allowed by TokenizedStrategy.

Validation result:
- The PoC shows `emergencyWithdraw()` creates redeemable WETH, then `report()` stakes it back into stETH and `maxRedeem(user)` returns to zero.

### M-04 Strategy4626 emergencyWithdraw does not materially free the normal ERC4626-held position

Status: RELUCTANTLY VALID
Severity: Medium
Confidence: High

Cross-reference analysis:
- Raised by both Expert 1 and Expert 2.
- Expert 1 classified Low; Expert 2 classified Medium.
- Verified by orchestrator PoC `Strategy4626EmergencyNoopPoC.t.sol`.

Economic feasibility:
- No external theft path.
- Impact occurs during emergency operations when the standard Yearn emergency unwind fails to free the normal vault-held position.
- Manual fallback functions exist, reducing severity, but reliance on a multi-step emergency runbook is material during time-sensitive incidents.

Technical disproof attempts:
- Checked whether inherited `_emergencyWithdraw()` uses `valueOfLST()` or `_freeStETH()`. It does not; it checks only loose `balanceOfLST()`.
- Checked whether normal Strategy4626 deposits leave material loose stETH. They do not; exposure sits in ERC4626 vault shares, with at most dust loose.

Validation result:
- The PoC shows emergency withdraw leaves vault shares unchanged and user redemption effectively unavailable except for dust.

## Low Findings

### L-01 Lido withdrawal return data and keeper claim payload use inconsistent ABI shapes

Status: VALID
Severity: Low
Confidence: High

Validation:
- `_initiateLSTWithdrawal()` returns `abi.encode(requestIds)` where `requestIds` is a `uint256[]`.
- `_claimLSTWithdrawal()` decodes supplied bytes as `(uint256)`.
- The current tests manually decode the array and re-encode the first element, confirming the returned bytes are not directly consumable by the claim function.

Budget-protection note:
- This is an automation/integration DoS, not a fund-drain path.
- Low severity is appropriate because operators can decode/re-encode or use emergency batch claim.

### L-02 StrategyAprOracle returns a constant APR for all strategies and deltas

Status: VALID
Severity: Low
Confidence: High

Validation:
- `aprAfterDebtChange(address,int256)` ignores both inputs and returns `4e16`.
- If used in production allocation, it can misprice shutdown, full, paused, depegged, or negative-yield strategies.

Budget-protection note:
- No direct exploit path from this contract alone.
- Low severity is appropriate unless the oracle is confirmed as production allocator input.

## Dismissed or Downgraded Candidates

- Slither strict equality results: dismissed as style/noise for zero checks, pending-redemption guard, and dust checks.
- Slither factory reentrancy result: downgraded/dismissed. The state write after deployment can create duplicate deployments under exotic reentrancy from a malicious vault symbol/asset path, but the created strategies remain factory-configured and this was not shown to create fund loss.
- Slither zero-address results: low operational hygiene. TokenizedStrategy rejects zero management/performance fee recipient during strategy initialization; factory zero addresses can break future deployments but do not let an attacker steal initialized strategy funds.
- `setReportBuffer()` above `MAX_BPS`: management-only misconfiguration. It can revert accounting but is directly recoverable by management setting a sane value.
- Curve deposit route slippage: dismissed for ETH to stETH deposits because `_stake()` uses Curve only if `get_dy > amount` and sets minimum out to `_amount`; otherwise it stakes through Lido.
- First-depositor inflation against TokenizedStrategy: dismissed because Yearn tracks `totalAssets` internally rather than raw token balance for share conversion.
