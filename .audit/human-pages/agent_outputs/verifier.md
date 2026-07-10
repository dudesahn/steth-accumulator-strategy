# Verifier Results

## Summary Table

| ID | Classification | Severity | Disposition |
| --- | --- | --- | --- |
| C1: shutdown/report/tend restakes WETH | validated by PoC | Medium | findings.jsonl |
| C2: Strategy4626 emergencyWithdraw does not redeem vault | validated behavior, downgraded | Low / operational note | report note only |
| C3: Lido queue return-data mismatch | validated by PoC | Medium | findings.jsonl |
| C4: Strategy4626 no nonzero/min-share check | plausible / deployment-conditional | Medium conditional, Low for vetted vaults | conditional finding or merge with C7 |
| C5: Strategy4626 deposit limit ignores loose WETH also deployed | validated | Medium when deposits are open and idle WETH exists; otherwise Low | findings.jsonl if public/allowlisted deposits are in scope |
| C6: factory zero profit unlock enables report front-run | plausible / deployment-conditional | Medium if public deposits and material unreported gains; otherwise Low | conditional findings.jsonl |
| C7: external ERC4626 NAV/liveness manipulation | plausible / deployment-conditional | Low / info as a standalone trust-boundary note | report note, merge with C4 |
| C8: manual swap stale-accounting withdrawal race | downgraded | Low | report note only |
| C9: zero-address factory config and unbounded reportBuffer | downgraded | Info / Low | report note only |
| C10: duplicate deployment reentrancy and setReferral(0) | false_positive / rejected | None | no entry |

## Gate Reviews

### C1: Shutdown report/tend can re-stake WETH liquidity

- Reachability: keeper or management can still call inherited `report()` and `tend()` after shutdown (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1081-1085`, `1314-1318`, `1325-1335`).
- Validation Chain: local `_harvestAndReport` stakes loose WETH before accounting (`src/BaseLSTAccumulator.sol:146-155`), `_tend` stakes `_totalIdle` directly (`src/BaseLSTAccumulator.sol:165-166`), and both can route into stETH or Strategy4626 vault exposure (`src/Strategy.sol:51-69`, `src/Strategy4626.sol:29-42`). The new PoC proves shutdown plus emergency withdrawal creates WETH liquidity, then keeper `tend()` restakes it and reduces user redeemability (`.audit/human-pages/poc_tests/ShutdownRestakeLiquidity.t.sol:10-29`).
- Math Bounds: report stakes up to `min(balanceOfAsset(), availableDepositLimit(address(this)))`; `address(this)` is whitelisted and the local limit does not check shutdown (`src/BaseLSTAccumulator.sol:64`, `126-130`).
- State Preconditions: idle WETH exists after `emergencyWithdraw`, manual swap, Lido claim, or `stakeAsset=false` operation.
- Economic Viability: no direct theft, but it can remove emergency/user-exit liquidity because withdrawals are capped to loose WETH (`src/BaseLSTAccumulator.sol:133-143`).
- Environment: applies to base Strategy and Strategy4626; worse when keepers are automated or shutdown playbooks do not pause them.
- Verdict: PoC-validated Medium; formal finding.

### C2: Strategy4626 inherited emergencyWithdraw does not redeem vaulted position

- Reachability: emergencyAdmin or management can call shutdown then inherited `emergencyWithdraw` (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1337-1340`, `1356-1363`).
- Validation Chain: the PoC deposits into Strategy4626, records vault shares, calls shutdown plus `emergencyWithdraw(type(uint256).max)`, and asserts vault shares are unchanged (`.audit/human-pages/poc_tests/Strategy4626EmergencyWithdrawNoop.t.sol:11-26`).
- Math Bounds: final adjusted PoC tolerates pre-existing stETH dust; the command result showed only dust was freed and the ERC4626 vault share position was unchanged.
- State Preconditions: only applies when value is vaulted as wstETH/ERC4626 shares and the operator has not first called `manualRedeem` / `manualUnwrap` (`src/Strategy4626.sol:103-115`).
- Economic Viability: operational delay or failed emergency runbook, not an attacker-triggered loss; separate emergency hatches exist.
- Environment: Strategy4626 only; impact increases if the external vault itself is paused or blocks redemption.
- Verdict: validated behavior, but downgraded to Low/report note because it is trusted emergency flow with explicit manual escape hatches.

### C3: Lido withdrawal initiation return data does not match claim decoder

- Reachability: management calls `initiateLSTWithdrawal`, keeper calls `claimLSTWithdrawal(bytes)` (`src/BaseLSTAccumulator.sol:259-263`, `269-272`).
- Validation Chain: Strategy returns `abi.encode(uint256[] requestIds)` (`src/Strategy.sol:91-99`) but claim decodes a scalar `uint256` (`src/Strategy.sol:104-109`). The new PoC proves the natural roundtrip decodes to `32`, reverts with `Invalid request`, leaves `pendingRedemptions` nonzero, and scalar `abi.encode(requestIds[0])` clears it (`.audit/human-pages/poc_tests/WithdrawalQueueClaimDataMismatch.t.sol:25-44`).
- Math Bounds: ABI dynamic-array encoding starts with the offset word `0x20`; the PoC asserts `abi.decode(returnData, (uint256)) == 32`.
- State Preconditions: a pending Lido withdrawal exists and the keeper uses the returned initiation bytes directly.
- Economic Viability: no theft, but reports are hard-blocked while `pendingRedemptions != 0` (`src/BaseLSTAccumulator.sol:146-148`) until operators pass scalar id data or use privileged recovery.
- Environment: applies to the intended Lido queue flow; mock PoC isolates the ABI shape.
- Verdict: validated Medium; formal finding.

### C4: Strategy4626 deposits without checking nonzero/minimum vault shares

- Reachability: Strategy4626 `_stake` wraps all stETH and calls `vault.deposit(wstETHBalance, address(this))` (`src/Strategy4626.sol:32-42`).
- Validation Chain: returned ERC4626 shares are ignored, while inherited deposit accounting credits the original WETH and mints strategy shares after deployment returns (`lib/tokenized-strategy/src/TokenizedStrategy.sol:963-975`). OZ-style ERC4626 math rounds shares down and does not require nonzero shares on deposit (`lib/openzeppelin-contracts/contracts/token/ERC20/extensions/ERC4626.sol:153-159`, `199-200`).
- Math Bounds: zero/dust shares are possible only under an inflated, fee-heavy, or otherwise unfavorable vault share price relative to the deposit amount.
- State Preconditions: selected vault must be vulnerable/manipulable or already inflated; deposits must be open or allowlisted.
- Economic Viability: high impact if principal is donated to a vault while strategy shares are minted; low likelihood for vetted wstETH vaults.
- Environment: deployment-conditional; not proven against the example vault.
- Verdict: plausible conditional issue. Include as a conditional finding only if Strategy4626 is intended to support arbitrary ERC4626 vaults; otherwise merge into the C7 integration-risk note.

### C5: Strategy4626 availableDepositLimit ignores pre-existing loose WETH

- Reachability: public/allowlisted deposit reaches inherited `_deposit`; `_deposit` deploys the strategy's full loose WETH balance, not just the new depositor's amount (`lib/tokenized-strategy/src/TokenizedStrategy.sol:963-969`).
- Validation Chain: Strategy4626 limit checks external `vault.maxDeposit(address(this))` against the new deposit capacity (`src/Strategy4626.sol:55-63`), but `_stake` later deposits all loose wstETH into the vault without a second capacity check (`src/Strategy4626.sol:32-42`).
- Math Bounds: a deposit can satisfy `assets <= availableDepositLimit(receiver)` while `assets + preExistingLooseWETH` exceeds remaining vault capacity.
- State Preconditions: loose WETH exists from donation, `stakeAsset=false`, manual swap, queue claim, or emergency unwinding; the ERC4626 vault has finite capacity.
- Economic Viability: can cause deposit reverts or re-deploy exit liquidity. Creating the condition by donation has cost, but naturally idle WETH makes the grief cheap.
- Environment: Strategy4626 only; relevant when deposits are open/allowlisted and the vault has a meaningful `maxDeposit` cap.
- Verdict: validated invariant break. Medium if public deposits and idle WETH are expected; formal finding if those assumptions are in report scope.

### C6: Factory-created Strategy4626 disables profit locking

- Reachability: factory deployment sets `profitMaxUnlockTime` to zero (`src/Strategy4626Factory.sol:62-64`); public/allowlisted users can deposit before keeper reports when deposits are open.
- Validation Chain: deposits mint against last recorded accounting (`lib/tokenized-strategy/src/TokenizedStrategy.sol:505-510`, `836-851`, `971-975`), while unreported vault gains enter only on report (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1095-1117`, `1245-1247`). Profit-lock share minting is skipped when unlock time is zero (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1164-1183`).
- Math Bounds: attacker captures a pro-rata share of unreported profit by depositing at stale PPS immediately before report.
- State Preconditions: deposits open or attacker allowlisted, material unreported Strategy4626 vault gain, predictable/reportable keeper action, and later liquidity to exit.
- Economic Viability: value transfer from existing shareholders to report front-runners; no protocol insolvency.
- Environment: factory Strategy4626 deployments only; lower risk if deposits stay closed/allowlisted.
- Verdict: plausible deployment-conditional Medium; conditional finding when public deposits are intended.

### C7: External ERC4626 vault NAV/liveness manipulation

- Reachability: Strategy4626 trusts only `vault.asset() == wstETH` at construction (`src/Strategy4626.sol:20-23`) and then depends on `maxDeposit`, `convertToAssets`, `previewWithdraw`, `maxRedeem`, and `redeem` (`src/Strategy4626.sol:55-63`, `69-75`, `77-96`).
- Validation Chain: source supports the trust boundary, but no specific endorsed vault manipulation was proven.
- Math Bounds: false NAV can inflate/deflate reports; `maxRedeem == 0` or reverting `redeem` can block exits.
- State Preconditions: malicious, paused, or economically manipulable ERC4626 vault selected and opened by management.
- Economic Viability: severe if governance endorses an unsafe vault, but this is primarily external-dependency selection risk.
- Environment: deployment-conditional; health checks can bound some report shocks, though management can disable one check.
- Verdict: plausible but too broad for a standalone finding without a concrete vault. Report note or merge into C4.

### C8: Management manual swap stale-accounting withdrawal race

- Reachability: management can call `manualSwapToAsset` (`src/BaseLSTAccumulator.sol:241-245`, `src/Strategy.sol:74-81`), and users can withdraw loose WETH before the next report.
- Validation Chain: withdrawals burn shares and pay WETH against current recorded accounting (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1008-1044`); manual-swap losses are recognized later in `report()` (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1081-1247`).
- Math Bounds: faster withdrawers can exit before a loss is socialized if a loss-making swap creates idle WETH.
- State Preconditions: management realizes a loss and does not report in the same operational bundle.
- Economic Viability: value shift among users, but it requires trusted management action and preventable sequencing.
- Environment: expected operator-flow hazard, not an untrusted attack.
- Verdict: downgraded Low; report note only with runbook guidance to pair loss-making swaps and reports.

### C9: Factory zero addresses and unbounded reportBuffer

- Reachability: factory constructor/setter accept role values without zero checks (`src/Strategy4626Factory.sol:24-35`, `72-83`); management can set arbitrary `reportBuffer` (`src/BaseLSTAccumulator.sol:198-200`).
- Validation Chain: zero pending management or performance fee recipient makes future deployments revert through inherited checks (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1502-1504`, `1572-1577`), while `reportBuffer > MAX_BPS` underflows `MAX_BPS - reportBuffer` (`src/BaseLSTAccumulator.sol:177-178`).
- Math Bounds: reportBuffer above 10_000 reverts checked arithmetic; zero factory management bricks future `setAddresses`.
- State Preconditions: deployer or trusted management misconfiguration.
- Economic Viability: no untrusted exploit; reportBuffer is correctable by management unless role configuration is also broken.
- Environment: configuration hygiene.
- Verdict: Info/Low only. Do not keep as Medium; report notes only.

### C10: Factory duplicate deployment reentrancy and setReferral(0)

- Reachability: duplicate-deployment theory depends on reentering during `symbol()` or `asset()` reads before `deployments[_vault]` is written (`src/Strategy4626Factory.sol:43-68`, `src/Strategy4626.sol:20-21`).
- Validation Chain: lanes correctly rejected this. `symbol()` and `asset()` are view/static calls, the constructor approval targets fixed wstETH rather than the vault (`src/Strategy4626.sol:25-26`), and later external calls are to the freshly deployed strategy setters (`src/Strategy4626Factory.sol:52-64`).
- Math Bounds: no viable duplicate-write or role-takeover path remains.
- State Preconditions: malicious vault cannot statefully reenter from a static context.
- Economic Viability: public deployment front-run can only create the same factory-configured strategy; caller receives no role.
- Environment: `setReferral(0)` is management-only and zero is valid/no-referral data for Lido submit (`src/Strategy.sol:67-68`, `128-130`).
- Verdict: false positive/rejected. No finding or note required beyond optional scanner-triage text.

## PoC Review

- Build and baseline are clean per orchestrator: `forge build --force --skip 'src/test/*PoC*.t.sol'` succeeded with warnings only, and `env ETH_RPC_URL=https://ethereum.publicnode.com forge test -vv --no-match-path 'src/test/*PoC*.t.sol' --fork-url https://ethereum.publicnode.com` passed 46 tests across 8 suites.
- C1 PoC command: `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --contracts .audit/human-pages/poc_tests --match-path .audit/human-pages/poc_tests/ShutdownRestakeLiquidity.t.sol -vvv --fork-url https://ethereum.publicnode.com`. Result: 1 passed. The PoC shows `shutdownStrategy()` plus `emergencyWithdraw(type(uint256).max)` creates liquid WETH and positive `maxRedeem(user)`, then keeper `tend()` reduces WETH and `maxRedeem(user)` while increasing strategy stETH (`.audit/human-pages/poc_tests/ShutdownRestakeLiquidity.t.sol:10-29`).
- C2 PoC command: `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --contracts .audit/human-pages/poc_tests --match-path .audit/human-pages/poc_tests/Strategy4626EmergencyWithdrawNoop.t.sol -vvv --fork-url https://ethereum.publicnode.com`. Result: 1 passed. The PoC shows `emergencyWithdraw(type(uint256).max)` leaves Strategy4626 vault shares unchanged and frees only loose stETH dust (`.audit/human-pages/poc_tests/Strategy4626EmergencyWithdrawNoop.t.sol:11-26`). Earlier exact-zero failure was explained by 1 wei loose stETH dust; the adjusted PoC is the relevant result.
- C3 PoC command: `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --contracts .audit/human-pages/poc_tests --match-path .audit/human-pages/poc_tests/WithdrawalQueueClaimDataMismatch.t.sol -vvv --fork-url https://ethereum.publicnode.com`. Result: 1 passed. The PoC confirms the ABI mismatch: returned `uint256[]` data decodes as scalar `32`, direct `claimLSTWithdrawal(returnData)` reverts, `pendingRedemptions` remains nonzero, and `claimLSTWithdrawal(abi.encode(requestIds[0]))` clears it (`.audit/human-pages/poc_tests/WithdrawalQueueClaimDataMismatch.t.sol:25-44`).

## Severity Calibration

- C1: High exit-liquidity impact x Low/Medium role-limited likelihood = Medium. Keeper automation makes the likelihood meaningful despite role restriction, and the shutdown-restake PoC confirms the impact on WETH balance and `maxRedeem(user)`.
- C2: Medium emergency-operability impact x Low trusted-operator likelihood = Low. PoC-valid but not Medium because manual hatches exist and no untrusted actor triggers it.
- C3: Medium report/accounting DoS impact x Medium natural-API-misuse likelihood = Medium. PoC confirms the validation chain.
- C4: High potential loss impact x Low vault-condition likelihood = Medium conditional. Low/info for vetted, non-manipulable vaults.
- C5: Medium liquidity/capacity DoS impact x Low/Medium likelihood = Medium only when public deposits and idle WETH are realistic; otherwise Low.
- C6: Medium dilution impact x Low/Medium public-report-timing likelihood = Medium conditional; Low if deposits remain closed/allowlisted.
- C7: High dependency-failure impact x Low likelihood for vetted vaults = report-note severity unless a concrete vault is shown unsafe.
- C8: Medium value-shift impact x Low trusted-management sequencing likelihood = Low.
- C9: Low/Medium liveness impact x Low trusted-misconfiguration likelihood = Info/Low.
- C10: no validated impact or viable likelihood = rejected.

## Findings Bundle Recommendations

Write findings.jsonl entries for:

- C1 as Medium: keeper report/tend can redeploy shutdown or paused idle WETH into stETH/vault exposure.
- C3 as Medium: Lido withdrawal return data is not roundtrippable into `claimLSTWithdrawal(bytes)`.
- C5 as Medium/Low based on final scope: Strategy4626 deposit-capacity checks ignore loose WETH that inherited `_deposit` also deploys.
- C6 as conditional Medium if factory Strategy4626 deployments are expected to open public deposits: zero profit unlock enables report-front-run dilution.
- C4 only as a conditional ERC4626-integration finding if arbitrary vault support is an intended feature; otherwise merge it into the C7 report note.

Keep as report notes only:

- C2: PoC-confirmed Strategy4626 emergencyWithdraw only handles loose stETH/dust; document the required `manualRedeem` -> `manualUnwrap` -> `emergencyWithdraw` sequence.
- C7: external ERC4626 vault trust, NAV, and liveness assumptions.
- C8: management should bundle loss-realizing manual swaps with report/accounting updates.
- C9: factory zero-address hygiene and `reportBuffer <= MAX_BPS` hardening.

Reject/no output entry:

- C10 duplicate deployment reentrancy and `setReferral(0)`.
