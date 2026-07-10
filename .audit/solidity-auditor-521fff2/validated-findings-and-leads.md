# Validated Findings and Leads

Commit: `521fff28ad978a37115be8995a1d631611fa1d3d`
Branch: `review`
Scope: `src/BaseLSTAccumulator.sol`, `src/Strategy.sol`, `src/Strategy4626.sol`, `src/Strategy4626Factory.sol`, `src/periphery/StrategyAprOracle.sol`

This file is the post-validation output from the Pashov `solidity-auditor` two-wave, all-lane run. X-ray artifacts were used only as orientation. Raw agent findings were deduped, source-traced, and classified as findings, leads, or rejected trails.

## Validated Findings

### F-01: Manual or emergency unwinds expose idle WETH before accounting records the unwind loss

Severity: Medium
Contracts: `BaseLSTAccumulator`, inherited `TokenizedStrategy`
Functions: `manualSwapToAsset`, `_emergencyWithdraw`, `availableWithdrawLimit`, `TokenizedStrategy._withdraw`
Primary lanes: agent 11

`manualSwapToAsset()` lets management convert stETH-side value back into idle WETH, and `_emergencyWithdraw()` can do the same with zero slippage protection after shutdown. Neither path updates TokenizedStrategy's stored `totalAssets`; that accounting only changes during report or user deposit/withdraw accounting. At the same time, `availableWithdrawLimit()` immediately returns the new idle WETH balance, and TokenizedStrategy withdrawals price shares against the stale stored total.

Concrete path:

1. Last report records 100 WETH-equivalent assets and 100 shares.
2. The strategy holds no idle WETH, only stETH-side exposure.
3. Management calls `manualSwapToAsset(100e18, 90e18)` during a 10 percent stETH discount, or emergency shutdown calls `_emergencyWithdraw()` with `_minOut = 0`.
4. The strategy now holds 90 WETH, but stored `totalAssets` is still 100.
5. A shareholder redeems 50 shares before the next report. `availableWithdrawLimit()` allows the withdrawal because 90 WETH is idle, and share conversion still values 50 shares at 50 WETH.
6. The first redeemer receives 50 WETH instead of the fair post-loss 45 WETH, shifting 5 WETH of loss to remaining shareholders.

Why this passed validation:

- `manualSwapToAsset()` performs the LST-to-asset swap without a report.
- `_emergencyWithdraw()` swaps with `_minOut = 0`.
- `availableWithdrawLimit()` exposes all idle WETH.
- TokenizedStrategy `_withdraw()` subtracts assets from stored accounting only when the redeem happens, after share conversion and max-withdraw checks have used stale values.

Recommended fix: after any manual or emergency unwind that changes liquid WETH, either force a successful report before withdrawals can use the new idle balance, or set a stale-accounting flag that makes `availableWithdrawLimit()` return zero until the unwind is reported. Consider slippage-bound emergency unwinds or a report-coupled manual unwind helper.

### F-02: Pending Lido redemptions are excluded from deposit-limit accounting

Severity: Low/Medium
Contracts: `BaseLSTAccumulator`, `Strategy`
Functions: `_depositLimit`, `availableDepositLimit`, `initiateLSTWithdrawal`, `claimLSTWithdrawal`
Primary lanes: agents 5 and 12

`depositLimit` is enforced against `estimatedTotalAssets()`, but queued Lido withdrawal value disappears from `balanceOfLST()` while only the scalar `pendingRedemptions` tracks it. Deposits are not blocked while `pendingRedemptions > 0`, so open or allowed depositors can fill capacity that exists only because existing value is temporarily in the Lido queue.

Concrete path:

1. `depositLimit = 100e18`, `reportBuffer = 0`, deposits are open, and the strategy holds 100e18 stETH.
2. `_depositLimit()` returns zero because estimated assets equal the limit.
3. Management calls `initiateLSTWithdrawal(60e18)`. The strategy increments `pendingRedemptions` and transfers 60e18 stETH into the queue.
4. `estimatedTotalAssets()` now sees only the remaining 40e18 stETH and omits the pending 60e18.
5. `availableDepositLimit()` returns 60e18, so a user can deposit 60e18 WETH.
6. When the Lido request is later claimed, the strategy has roughly 160e18 WETH-equivalent exposure against a configured 100e18 cap.

Why this passed validation:

- `_depositLimit()` uses `estimatedTotalAssets()`.
- `estimatedTotalAssets()` counts idle asset plus LST value, but not `pendingRedemptions`.
- `initiateLSTWithdrawal()` increments `pendingRedemptions` and moves value out of direct balances.
- Deposits check `availableDepositLimit()` and are not gated by the pending-redemption state.

Recommended fix: include `pendingRedemptions` in the cap-side asset estimate, or make `availableDepositLimit()` return zero whenever `pendingRedemptions != 0`.

### F-03: Forced loose wstETH can DoS Strategy4626 reports when the downstream vault has no capacity

Severity: Medium
Contracts: `Strategy4626`, `BaseLSTAccumulator`
Functions: `_stake`, `_harvestAndReport`, `availableDepositLimit`
Primary lanes: agent 12

`BaseLSTAccumulator._harvestAndReport()` always calls `_stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this))))`. In Strategy4626, `_stake(0)` still wraps all loose stETH and deposits the full loose wstETH balance into the downstream vault. An untrusted sender can transfer wstETH directly to the strategy, causing the next report to require a vault deposit even when `availableDepositLimit()` correctly reports zero capacity.

Concrete path:

1. The downstream ERC4626 vault returns `maxDeposit(address(strategy)) == 0`.
2. The strategy has no idle WETH and no pending redemptions.
3. An attacker transfers 1 wei of wstETH directly to the Strategy4626 instance.
4. On report, `_harvestAndReport()` calls `_stake(0)`.
5. `Strategy4626._stake(0)` skips no work after `super._stake(0)`, sees the forced wstETH balance, and calls `vault.deposit(1, address(this))`.
6. A standards-compliant capped vault reverts because deposit capacity is zero, blocking report.

Why this passed validation:

- Forced ERC20 transfers into the strategy are permissionless.
- Strategy4626's `_stake()` lacks an `_amount == 0` early return and deposits all loose wstETH.
- `availableDepositLimit()` respects downstream `maxDeposit`, but `_stake()` does not cap the actual vault deposit by the current remaining capacity.

Recommended fix: cap the vault sweep by `vault.maxDeposit(address(this))` after wrapping, skip the vault deposit when capacity is zero, and leave any surplus loose wstETH valued in place until capacity returns or an explicit maintenance path handles it.

## Validated Leads

### L-01: Lido request return data and claim data use incompatible ABI shapes

Contracts: `Strategy`, `BaseLSTAccumulator`
Primary lanes: agents 3, 4, 8; corroborated by agents 2, 5, 7, 9, 12

`Strategy._initiateLSTWithdrawal()` returns `abi.encode(uint256[] requestIds)`, but `Strategy._claimLSTWithdrawal()` decodes the claim bytes as a scalar `uint256`. Passing the raw return bytes from initiation into claim decodes the dynamic-array offset `0x20` as request id `32`, not the actual request id. The current tests work around this by decoding `returnData` as `uint256[]` and passing `abi.encode(requestIds[0])`.

This is a validated operational lead rather than a promoted finding because the intended keeper tooling can use the test shape safely, and the path is keeper/management controlled. If the returned bytes are documented or consumed directly, it becomes a report-blocking bug because `pendingRedemptions` remains nonzero until a correctly encoded id is claimed or manually cleared.

Recommended fix: make both sides use one data shape. For the one-request flow, either return `abi.encode(requestIds[0])` or decode `(uint256[] memory requestIds)` in `_claimLSTWithdrawal()`.

### L-02: Strategy4626 can advertise an executable max deposit that becomes too large after a favorable Curve fill

Contracts: `Strategy4626`, `Strategy`
Primary lanes: agents 1, 3, 5, 7, 9, 10

`Strategy4626.availableDepositLimit()` converts the downstream vault's `maxDeposit(address(this))` from wstETH units into stETH value. The staking path can route through Curve when it returns more stETH than the input WETH, then Strategy4626 wraps and deposits all resulting wstETH. With a finite downstream cap, a user can pass the strategy's precheck but the final vault deposit can revert because the favorable fill created more wstETH than the cap allowed.

Recommended fix: apply a post-stake capacity cap before `vault.deposit()`, leave surplus wstETH loose, or add explicit headroom when translating vault capacity into a WETH deposit limit.

### L-03: Strategy4626 emergency withdrawal does not reach vault-held value by itself

Contracts: `Strategy4626`, `BaseLSTAccumulator`, inherited TokenizedStrategy
Primary lanes: agents 8 and 12

The inherited shutdown/emergency withdrawal path reaches `BaseLSTAccumulator._emergencyWithdraw()`, which only checks direct stETH. A Strategy4626 instance normally holds value as vault shares or wstETH, and the automated emergency path does not call `manualRedeem()` or `manualUnwrap()`. Operators can still recover through the manual emergency helpers, so this is an operational lead rather than a direct exploit.

Recommended fix: override Strategy4626 emergency withdrawal to redeem/unwrap enough vault-held value before calling the base swap, or document that emergency withdrawal is a multi-step manual procedure for Strategy4626 instances.

### L-04: Permissionless factory deployment stamps live role defaults and one-shot vault registry state

Contracts: `Strategy4626Factory`, `Strategy4626`
Primary lanes: agents 2, 4, 6, 7, 11, 12

Anyone can call `newStrategy4626()` for any ERC4626 vault whose asset is wstETH. The factory immediately stamps current role defaults and records a single deployment for that vault. The caller does not gain privileges, and management still needs to accept the strategy, but the factory event and mapping can contain arbitrary vault integrations created before off-chain review or immediately before role defaults rotate.

Recommended fix: require a management allowlist/reservation for vault deployments, or make downstream consumers treat factory deployments as unendorsed until management acceptance and an allowlist flag are present.

### L-05: `reportBuffer` has no `MAX_BPS` bound

Contracts: `BaseLSTAccumulator`
Primary lanes: agents 1 and 11; x-ray invariant I-4

`estimatedTotalAssets()` computes `MAX_BPS - reportBuffer`, but `setReportBuffer()` does not enforce `reportBuffer <= MAX_BPS`. Values above 100 percent revert valuation/report paths under checked arithmetic, while values near 100 percent are a strong management-controlled NAV lever. This is a trust-model lead because management controls the setter.

Recommended fix: add `require(_reportBuffer <= MAX_BPS, "!reportBuffer")` or equivalent.

## Rejected or Demoted Trails

- Factory duplicate deployment through reentrancy: rejected. The external calls to `_vault.symbol()` and `_vault.asset()` are view calls and are compiled as `STATICCALL`; a malicious vault cannot reenter and complete a state-changing factory deployment under static context.
- `stakeAsset` not honored by report/tend: demoted. Tests explicitly cover report staking while `stakeAsset` is false, so this appears to be intended keeper/report behavior rather than a bug by itself.
- `isDeployedStrategy()` reverts on arbitrary non-strategy input: demoted. It is a brittle view helper but no in-scope consumer relies on it as a user-facing invariant.
- Fixed `StrategyAprOracle` APR: demoted. It is a placeholder-like periphery value with no in-repo value-moving consumer.

## Verification Commands

```sh
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-contract WithdrawalQueueTest -vv --fork-url https://ethereum.publicnode.com
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-contract Strategy4626Test -vv --fork-url https://ethereum.publicnode.com
```

Results:

- `WithdrawalQueueTest`: 7 passed, 0 failed.
- `Strategy4626Test`: 5 passed, 0 failed.

