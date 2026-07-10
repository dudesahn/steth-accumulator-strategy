# Human Pages Findings

Human Pages adapter evidence only. This is not a final external synthesis report.

## Scope and Verification

Reviewed production source under `src/`, deployment scripts under `script/`, relevant inherited Yearn TokenizedStrategy/HealthCheck code under `lib/`, and existing tests excluding prior/generated PoC-style files. No `.scratchpad/` content was read or written.

Commands recorded:

```bash
forge build --force --skip 'src/test/*PoC*.t.sol'
env ETH_RPC_URL=https://ethereum.publicnode.com forge test -vv --no-match-path 'src/test/*PoC*.t.sol' --fork-url https://ethereum.publicnode.com
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --contracts .audit/human-pages/poc_tests --match-path .audit/human-pages/poc_tests/ShutdownRestakeLiquidity.t.sol -vvv --fork-url https://ethereum.publicnode.com
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --contracts .audit/human-pages/poc_tests --match-path .audit/human-pages/poc_tests/WithdrawalQueueClaimDataMismatch.t.sol -vvv --fork-url https://ethereum.publicnode.com
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --contracts .audit/human-pages/poc_tests --match-path .audit/human-pages/poc_tests/Strategy4626EmergencyWithdrawNoop.t.sol -vvv --fork-url https://ethereum.publicnode.com
```

Results:

- Build succeeded with warnings only.
- Baseline fork tests: 46 passed, 0 failed, 0 skipped.
- Focused PoCs: 3 passed after one expected no-match adjustment and one dust-tolerance adjustment for the Strategy4626 emergency test.

## Validated Findings

### HP-M-01: Keeper report/tend can re-stake shutdown or emergency exit liquidity

Severity: Medium
Status: Validated
Confidence: High

After shutdown, Yearn TokenizedStrategy intentionally keeps `report()` and `tend()` callable. This strategy's `_harvestAndReport` stakes loose WETH before reporting, and `_tend` stakes the supplied idle WETH directly. Neither path checks `TokenizedStrategy.isShutdown()` or `stakeAsset`.

Evidence:

- TokenizedStrategy allows report/tend after shutdown: `lib/tokenized-strategy/src/TokenizedStrategy.sol:1081`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1314`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1325`.
- `_harvestAndReport` stakes loose WETH: `src/BaseLSTAccumulator.sol:146`, `src/BaseLSTAccumulator.sol:152`.
- `_tend` stakes idle WETH: `src/BaseLSTAccumulator.sol:165`.
- User withdrawals remain capped to loose WETH: `src/BaseLSTAccumulator.sol:133`.
- Strategy staking routes WETH into stETH and Strategy4626 then into wstETH/vault exposure: `src/Strategy.sol:51`, `src/Strategy4626.sol:29`.

PoC:

- `.audit/human-pages/poc_tests/ShutdownRestakeLiquidity.t.sol`
- Result: passed. The PoC shows `shutdownStrategy()` plus `emergencyWithdraw(type(uint256).max)` creates WETH liquidity and positive user `maxRedeem`, then keeper `tend()` reduces WETH and `maxRedeem` while increasing stETH exposure.

Impact:

No direct theft, but keeper/management can undo emergency liquid-exit state and reduce immediately withdrawable liquidity. This is especially risky with automated keepers or shutdown runbooks that do not pause tending/reporting.

Suggested remediation:

- In `_harvestAndReport`, skip `_stake(...)` when `TokenizedStrategy.isShutdown()` is true.
- In `_tend`, no-op or revert when shutdown.
- Consider respecting `stakeAsset == false` in report/tend staking paths, or introduce a separate explicit maintenance flag.

### HP-M-02: Lido withdrawal initiation return data is not round-trippable into claim

Severity: Medium
Status: Validated
Confidence: High

`initiateLSTWithdrawal` returns bytes from `_initiateLSTWithdrawal`. The stETH implementation calls Lido `requestWithdrawals`, receives a `uint256[] requestIds`, and returns `abi.encode(requestIds)`. The paired claim function decodes `_claimData` as a scalar `uint256`. Passing the returned bytes directly to `claimLSTWithdrawal` decodes the ABI dynamic-array offset `32`, not the request id.

Evidence:

- Initiation increments pending redemptions and returns child bytes: `src/BaseLSTAccumulator.sol:259`, `src/BaseLSTAccumulator.sol:262`.
- Lido request ids are `uint256[]`: `src/interfaces/IQueue.sol:5`.
- Strategy returns `abi.encode(requestIds)`: `src/Strategy.sol:97`, `src/Strategy.sol:99`.
- Claim decodes scalar `uint256`: `src/Strategy.sol:104`, `src/Strategy.sol:105`.
- Reports revert while pending redemptions remain: `src/BaseLSTAccumulator.sol:146`, `src/BaseLSTAccumulator.sol:147`.

PoC:

- `.audit/human-pages/poc_tests/WithdrawalQueueClaimDataMismatch.t.sol`
- Result: passed. The PoC shows the returned bytes decode as scalar `32`, direct claim reverts and leaves `pendingRedemptions` nonzero, while `abi.encode(requestIds[0])` succeeds and clears pending redemptions.

Impact:

Funds are not stolen, but the natural management-to-keeper bytes handoff fails. The strategy remains in the pending-redemption report lock until operators transform the data, use emergency batch claim, or manually clear pending redemptions.

Suggested remediation:

- Make `_claimLSTWithdrawal` decode `uint256[]` and claim the expected id(s), or make `_initiateLSTWithdrawal` return scalar-encoded claim data matching the claim decoder.
- Add regression tests that pass initiation return data directly into the claim path.

## Plausible / Deployment-Conditional Findings

### HP-C-01: Strategy4626 deposit limit can ignore pre-existing loose WETH

Severity: Medium when public/allowlisted deposits and finite vault capacity are in scope; otherwise Low
Status: Plausible / deployment-conditional
Confidence: Medium

Strategy4626 caps a new depositor using `vault.maxDeposit(address(this))`, but inherited `_deposit` deploys the strategy's full loose WETH balance after transferring the user's assets. If loose WETH already exists from donation, `stakeAsset=false`, manual swap, queue claim, or emergency unwinding, a deposit that is individually within `availableDepositLimit` can still push the total deployed amount above vault capacity.

Evidence:

- Inherited `_deposit` deploys `_asset.balanceOf(address(this))`: `lib/tokenized-strategy/src/TokenizedStrategy.sol:963`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:967`.
- Strategy4626 checks `vault.maxDeposit(address(this))`: `src/Strategy4626.sol:55`, `src/Strategy4626.sol:59`.
- Strategy4626 deposits all resulting wstETH without rechecking capacity: `src/Strategy4626.sol:37`, `src/Strategy4626.sol:41`.

Impact:

Can revert otherwise valid deposits or re-deploy exit liquidity if idle WETH exists and the external vault has a finite cap.

Suggested remediation:

- Deploy only the newly deposited amount when enforcing per-deposit external vault capacity, or subtract existing loose WETH from Strategy4626 `availableDepositLimit`.
- Recheck external `maxDeposit` immediately before `vault.deposit`.

### HP-C-02: Factory-created Strategy4626 disables profit locking, enabling report-front-run dilution

Severity: Medium conditional
Status: Plausible / deployment-conditional
Confidence: Medium

The factory sets `profitMaxUnlockTime` to zero for every Strategy4626 deployment. Deposits mint against last recorded total assets. Unreported vault gains enter on `report()`. With zero profit unlock, a positive report immediately increases PPS instead of minting locked shares, so a depositor who enters immediately before a predictable report can share in gains that economically accrued before their deposit.

Evidence:

- Factory sets zero unlock time: `src/Strategy4626Factory.sol:64`.
- Deposits mint before updated report accounting: `lib/tokenized-strategy/src/TokenizedStrategy.sol:505`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:971`.
- Reports incorporate new total assets: `lib/tokenized-strategy/src/TokenizedStrategy.sol:1095`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1245`.
- Profit locking branch depends on nonzero unlock time: `lib/tokenized-strategy/src/TokenizedStrategy.sol:1164`.

Impact:

Potential dilution/value transfer from existing shareholders to report-front-running depositors when deposits are open and unreported Strategy4626 gains are material.

Suggested remediation:

- Avoid setting factory Strategy4626 profit unlock time to zero unless deposits remain tightly permissioned.
- If zero unlock is required, close deposits around reports or report before opening deposits after material vault gains.

### HP-C-03: Strategy4626 trusts external ERC4626 share minting, NAV, and liveness without local slippage/min-share guards

Severity: Medium conditional for arbitrary/manipulable vaults; Low/info for vetted vaults
Status: Plausible / deployment-conditional
Confidence: Medium-Low

Strategy4626 only verifies that the external vault asset is wstETH. It then trusts `vault.deposit`, `convertToAssets`, `previewWithdraw`, `maxRedeem`, and `redeem` for deposits, reports, and exits. `_stake` ignores the returned vault shares, so zero/dust-share or manipulated ERC4626 behavior can donate principal or distort reports if an unsafe vault is selected and deposits are opened.

Evidence:

- Constructor only checks `vault.asset() == wstETH`: `src/Strategy4626.sol:20`, `src/Strategy4626.sol:21`.
- Deposit return value is ignored: `src/Strategy4626.sol:37`, `src/Strategy4626.sol:41`.
- NAV trusts `convertToAssets`: `src/Strategy4626.sol:69`, `src/Strategy4626.sol:70`.
- Exit logic trusts `previewWithdraw`, `maxRedeem`, and `redeem`: `src/Strategy4626.sol:77`, `src/Strategy4626.sol:88`, `src/Strategy4626.sol:91`.

Impact:

An unsafe selected vault can cause deposit loss/donation, false profit/loss reports, or blocked exits. This is not proven against the example vault and should be treated as a vault-selection trust boundary unless arbitrary vault support is intended.

Suggested remediation:

- Check returned shares from `vault.deposit` against a minimum expected amount.
- Consider allowlisting vetted vaults or adding per-vault adapters.
- Add tests for zero-share deposit, manipulated `convertToAssets`, and `maxRedeem == 0`.

## Downgraded Notes

### Strategy4626 emergencyWithdraw only handles loose stETH/dust

PoC file `.audit/human-pages/poc_tests/Strategy4626EmergencyWithdrawNoop.t.sol` passed and showed inherited `emergencyWithdraw` leaves Strategy4626 vault shares unchanged. This is downgraded to a Low operational note because `manualRedeem` and `manualUnwrap` exist for emergency-authorized operators. Runbooks should document the required sequence for vaulted Strategy4626 exits.

### Management manual swaps can create stale-accounting withdrawal windows

A loss-making management `manualSwapToAsset` creates loose WETH before the loss is reported. Fast withdrawers can exit against stale accounting if management does not bundle a report. This is a trusted sequencing risk; report as a Low runbook note.

### Factory/configuration hardening

Factory constructor and `setAddresses` accept zero addresses; future deployments can be bricked or configured without keeper/emergency roles. `setReportBuffer` accepts values above `MAX_BPS`, causing checked underflow in `estimatedTotalAssets`. These are trusted-role configuration risks, not untrusted exploit paths.

### Direct Strategy4626 deployment script handoff

`script/Deploy4626.s.sol` logs a management handoff note but does not call the role setters used by `script/Deploy.s.sol` or the factory path. This is a deployment-process footgun if the direct script is used.

## Rejected / False Positive Candidates

- Factory duplicate deployment reentrancy: rejected. Reentry theory depends on stateful reentry during static/view calls or fresh strategy setters; no viable duplicate-deployment or role-takeover path was found.
- `setReferral(0)`: rejected. Zero is the default/no-referral value for Lido submit and the setter is management-only.
- Generic ERC777/no-return/fee-on-transfer asset concerns: rejected for intended WETH asset.
- Curve WETH-to-stETH quote manipulation: downgraded to revert/route-selection risk because the execution minimum is 1:1.

## Coverage Gaps

- No concrete malicious ERC4626 vault PoC was implemented for HP-C-03.
- HP-C-01 and HP-C-02 were verified by source trace and economic reasoning but not by executable PoC in this run.
- Static Slither was run broadly against `src/` and generated test/mock noise; final candidate selection ignored prior/generated PoC-file-derived signals.
