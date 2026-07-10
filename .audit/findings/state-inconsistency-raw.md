# Nemesis State Inconsistency Pass - Raw Hypotheses

## Coupled State Map

| State group | Intended invariant | Readers | Writers / mutators |
| --- | --- | --- | --- |
| `reportBuffer`, `MAX_BPS`, `estimatedTotalAssets` | Buffer must be within the BPS denominator before subtraction | `estimatedTotalAssets`, `_depositLimit`, `availableDepositLimit`, `_harvestAndReport` | `setReportBuffer` |
| WETH + stETH + wstETH/vault shares + TokenizedStrategy `totalAssets` | Reported assets should match economically controlled assets except intentional report buffer | TokenizedStrategy deposit/withdraw/report, health check | `_deployFunds`, `_stake`, `_swapLSTToAsset`, `_harvestAndReport`, `_freeStETH`, `manualRedeem`, `manualUnwrap`, report |
| `pendingRedemptions` + Lido queue request ids | Pending amount should be reduced only by successfully claimed queue value | `report`, `claimLSTWithdrawal`, `clearPendingRedemptions` | `initiateLSTWithdrawal`, `_claimLSTWithdrawal`, `manualClaimWithdrawals`, `clearPendingRedemptions` |
| Deposit gates: `openDeposits`, `allowed`, `depositLimit`, staking paused | Deposits should be admitted only for allowed receiver and available capacity | TokenizedStrategy max deposit/mint | setters, stETH `isStakingPaused`, `estimatedTotalAssets` |
| `stakeAsset` + idle WETH | Flag should clearly define which automated staking paths it controls | `_deployFunds`, `_harvestAndReport`, `_tend` | `setStakeAsset`, deposit, report, tend |
| APR oracle inputs and answer | APR should correspond to strategy and post-delta state if used for allocation | debt allocator/oracle callers | `aprAfterDebtChange` |

## SI-001: `reportBuffer` is not constrained to the denominator it subtracts from
- Coupled pair/group: `reportBuffer` and `MAX_BPS`.
- Invariant: `reportBuffer <= MAX_BPS` before `MAX_BPS - reportBuffer`.
- Breaking operation: `setReportBuffer()` accepts any `uint256`.
- Missing counterpart update/check: no upper-bound validation.
- Trigger sequence: management sets `_reportBuffer` above 10,000; `estimatedTotalAssets()` or `report()` reads it.
- Downstream reader/consequence: accounting and deposit/report paths revert on underflow.
- Masking code: none.
- Verification plan: Static trace; promote as Low.
- Status: Promoted.

## SI-002: Pending redemption amount is tracked, but claim request identity is untyped and not stored
- Coupled pair/group: `pendingRedemptions`, queue `requestIds`, and claim data bytes.
- Invariant: a successful normal claim should target the outstanding request id(s) created by initiation.
- Breaking operation: `_initiateLSTWithdrawal()` returns encoded array bytes; `_claimLSTWithdrawal()` expects encoded scalar bytes.
- Missing counterpart update/check: request ids are not stored on-chain and the bytes ABI is not self-describing.
- Trigger sequence: claim uses direct initiation return bytes.
- Downstream reader/consequence: wrong id/revert; `pendingRedemptions` remains nonzero; report remains blocked.
- Masking code: emergency `manualClaimWithdrawals` and `clearPendingRedemptions` can recover, but require privileged operational intervention.
- Verification plan: Static ABI trace plus tests.
- Status: Promoted as Low.

## SI-003: APR answer is disconnected from strategy state and delta
- Coupled pair/group: strategy capacity/shutdown/yield state and oracle return value.
- Invariant: `aprAfterDebtChange(strategy, delta)` should change when post-delta deployable capital or earning state changes.
- Breaking operation: constant return `4e16`.
- Missing counterpart update/check: no reads of strategy, delta, deposit limit, shutdown state, LST/vault APR, or allocation capacity.
- Trigger sequence: allocator queries a stale, shutdown, full, or unsupported strategy.
- Downstream reader/consequence: positive APR may be consumed as if deployable yield exists.
- Masking code: none in this contract.
- Verification plan: Static trace and oracle test review.
- Status: Promoted as Low with deployment-risk caveat.

## SI-004: `stakeAsset` and report-time staking intentionally diverge
- Coupled pair/group: `stakeAsset`, idle WETH, report/tend behavior.
- Invariant checked: whether disabling staking preserves idle WETH across all automated callbacks.
- Breaking operation: `_harvestAndReport()` does not check `stakeAsset`.
- Downstream reader/consequence: keeper report stakes idle WETH even when deposits did not.
- Verification: Existing tests explicitly assert this.
- Status: Downgraded to naming/documentation hazard.

## SI-005: Manual/emergency pending-redemption controls can realize losses by design
- Coupled pair/group: `pendingRedemptions`, queued claims, report.
- Invariant checked: clearing pending without an actual claim should be impossible unless intentional emergency recovery.
- Breaking operation: `clearPendingRedemptions()` can reduce the counter without claiming.
- Downstream reader/consequence: a later report may realize losses.
- Verification: Source comment explicitly warns of this behavior.
- Status: Eliminated as a documented emergency escape hatch, not an unintended inconsistency.
