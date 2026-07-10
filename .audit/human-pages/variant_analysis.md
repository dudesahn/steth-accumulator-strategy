# Variant Analysis

Variant analysis was run after verifier calibration against validated and plausible true-positive root causes.

## Shutdown Restaking Root Cause

Pattern:

```bash
rg -n "TokenizedStrategy\\.isShutdown|isShutdown\\(|shutdown|_harvestAndReport|_tend\\(|_stake\\(" src lib/tokenized-strategy/src/BaseStrategy.sol lib/tokenized-strategy/src/TokenizedStrategy.sol lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol -g '*.sol' -g '!*PoC*.t.sol'
```

Triage:

- `BaseStrategy` explicitly documents that post-shutdown reports should check `TokenizedStrategy.isShutdown()` before redeploying funds.
- `TokenizedStrategy` blocks deposits/mints on shutdown but keeps `report` and `tend` callable.
- Local `BaseLSTAccumulator._harvestAndReport` stakes loose WETH with no shutdown check.
- Local `BaseLSTAccumulator._tend` stakes `_totalIdle` with no shutdown check.
- `Strategy._stake` and `Strategy4626._stake` are the only local staking implementations.
- No local `TokenizedStrategy.isShutdown()` guard was found in strategy staking/report/tend paths.

Variant conclusion:

- The same root cause appears in both report and tend paths.
- The `stakeAsset` flag only gates `_deployFunds` and does not pause report/tend staking. This is a variant of the same liquidity-restaking issue.
- Strategy4626 inherits the same issue and can push funds into the external vault after shutdown.

## Lido Claim-Data ABI Root Cause

Pattern:

```bash
rg -n "abi\\.encode\\(|abi\\.decode\\(|requestWithdrawals|claimWithdrawal|claimWithdrawals|pendingRedemptions" src -g '*.sol' -g '!*PoC*.t.sol'
```

Triage:

- Only `src/Strategy.sol:99` returns `abi.encode(requestIds)` from a dynamic `uint256[]`.
- Only `src/Strategy.sol:105` decodes `_claimData` as scalar `uint256`.
- Existing tests decode the array and then pass `abi.encode(requestIds[0])`, confirming the direct returned bytes are not used in tests.
- Batch `manualClaimWithdrawals` separately accepts `uint256[]` and does not share the bytes mismatch.

Variant conclusion:

- No sibling ABI roundtrip mismatch was found.
- The bug is isolated to the single-request Lido queue initiate/claim API pair.

## Strategy4626 ERC4626 Integration Root Causes

Pattern:

```bash
rg -n "maxDeposit|previewWithdraw|convertToAssets|vault\\.deposit|vault\\.redeem|balanceOfWstETH|valueOfWstETH|profitMaxUnlockTime|setProfitMaxUnlockTime" src script -g '*.sol' -g '!*PoC*.t.sol'
```

Triage:

- `Strategy4626._stake` calls `vault.deposit(wstETHBalance, address(this))` and ignores returned shares.
- `Strategy4626.availableDepositLimit` uses `vault.maxDeposit(address(this))` but inherited `_deposit` deploys the whole loose WETH balance, not just the new deposit.
- `Strategy4626.valueOfWstETH` trusts `vault.convertToAssets`.
- `Strategy4626._freeStETH` trusts `previewWithdraw`, `maxRedeem`, and `redeem`.
- Factory-created Strategy4626 instances set profit unlock time to zero.

Variant conclusion:

- ERC4626 trust is concentrated in `Strategy4626`; no other local vault integrations were found.
- The min-share, maxDeposit-with-loose-WETH, NAV trust, and zero-profit-unlock concerns share a deployment-conditional external-vault risk profile.

## Configuration and Rejected Scanner Signals

Pattern:

```bash
rg -n "setReportBuffer|reportBuffer|setAddresses|_management|performanceFeeRecipient|setReferral|referral" src script -g '*.sol' -g '!*PoC*.t.sol'
```

Triage:

- `reportBuffer` has one setter and one arithmetic use; no other buffer variants exist.
- Factory role configuration appears only in constructor, `setAddresses`, and `newStrategy4626`.
- `setReferral(0)` is the only referral setter and is not a vulnerability.

Variant conclusion:

- No broader access-control bypass was found.
- Zero-address and reportBuffer issues remain trusted-role hardening notes.
