# DoS and Griefing Lane

## Coverage

Applied Human Pages Agent 10: DoS, Griefing & Fund Locking to the local production strategy, Strategy4626 extension, factory, relevant local interfaces, deployment scripts, and inherited Yearn TokenizedStrategy/BaseStrategy/HealthCheck paths that gate deposits, withdrawals, reports, tending, shutdown, and emergency exits.

Reviewed surfaces:
- User deposits/mints and withdrawals/redeems through inherited TokenizedStrategy: `lib/tokenized-strategy/src/TokenizedStrategy.sol:487`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:520`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:565`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:615`.
- Keeper/management report and tend: `lib/tokenized-strategy/src/TokenizedStrategy.sol:1081`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1314`.
- Shutdown and emergency withdraw: `lib/tokenized-strategy/src/TokenizedStrategy.sol:1337`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1356`.
- Base LST deposit/withdraw/report/tend/accounting controls: `src/BaseLSTAccumulator.sol:109`, `src/BaseLSTAccumulator.sol:126`, `src/BaseLSTAccumulator.sol:133`, `src/BaseLSTAccumulator.sol:146`, `src/BaseLSTAccumulator.sol:158`, `src/BaseLSTAccumulator.sol:165`, `src/BaseLSTAccumulator.sol:198`, `src/BaseLSTAccumulator.sol:259`, `src/BaseLSTAccumulator.sol:269`, `src/BaseLSTAccumulator.sol:279`.
- stETH/Lido/Curve/ETH handling: `src/Strategy.sol:36`, `src/Strategy.sol:38`, `src/Strategy.sol:51`, `src/Strategy.sol:74`, `src/Strategy.sol:91`, `src/Strategy.sol:104`, `src/Strategy.sol:116`.
- External ERC4626 vault wrapping, deposit, redeem, accounting, and manual exits: `src/Strategy4626.sol:20`, `src/Strategy4626.sol:29`, `src/Strategy4626.sol:55`, `src/Strategy4626.sol:69`, `src/Strategy4626.sol:77`, `src/Strategy4626.sol:103`, `src/Strategy4626.sol:110`.
- Factory public deployment and role configuration: `src/Strategy4626Factory.sol:24`, `src/Strategy4626Factory.sol:43`, `src/Strategy4626Factory.sol:72`.

## Candidates

### DGF-01: MEDIUM - Keeper report/tend can re-stake liquid exit funds after shutdown or after `stakeAsset` is disabled

`stakeAsset` only gates deposit-time deployment in `_deployFunds`: `src/BaseLSTAccumulator.sol:109` to `src/BaseLSTAccumulator.sol:112`. The report and tend paths ignore it: `_harvestAndReport` always stakes `min(balanceOfAsset(), availableDepositLimit(address(this)))` at `src/BaseLSTAccumulator.sol:146` to `src/BaseLSTAccumulator.sol:155`, and `_tend` always calls `_stake(_totalIdle)` at `src/BaseLSTAccumulator.sol:165` to `src/BaseLSTAccumulator.sol:166`. `tendTrigger` also ignores `stakeAsset` and shutdown, keying only off loose WETH and basefee at `src/BaseLSTAccumulator.sol:169` to `src/BaseLSTAccumulator.sol:170`.

This remains reachable after shutdown because TokenizedStrategy explicitly keeps `report` and `tend` callable in shutdown, while shutdown only prevents new deposits: `lib/tokenized-strategy/src/TokenizedStrategy.sol:1325` to `lib/tokenized-strategy/src/TokenizedStrategy.sol:1335`; the callable functions are at `lib/tokenized-strategy/src/TokenizedStrategy.sol:1081` to `lib/tokenized-strategy/src/TokenizedStrategy.sol:1085` and `lib/tokenized-strategy/src/TokenizedStrategy.sol:1314` to `lib/tokenized-strategy/src/TokenizedStrategy.sol:1318`.

The strategy also explicitly whitelists itself for local deposit-limit checks in the constructor at `src/BaseLSTAccumulator.sol:64`; local `availableDepositLimit` does not check TokenizedStrategy shutdown at `src/BaseLSTAccumulator.sol:126` to `src/BaseLSTAccumulator.sol:130`. As a result, post-shutdown `report`/`tend` can take WETH that was freed for user exits and convert it back into stETH through Curve/Lido (`src/Strategy.sol:51` to `src/Strategy.sol:69`) or into wstETH plus the external vault (`src/Strategy4626.sol:29` to `src/Strategy4626.sol:42`).

Impact: liquid WETH made available by management or emergencyAdmin can be pushed back into illiquid exposure, reducing `availableWithdrawLimit` to only remaining WETH at `src/BaseLSTAccumulator.sol:133` to `src/BaseLSTAccumulator.sol:143`, which then caps inherited withdrawals/redeems via `lib/tokenized-strategy/src/TokenizedStrategy.sol:895` to `lib/tokenized-strategy/src/TokenizedStrategy.sol:937`. In an emergency, `emergencyWithdraw` frees funds through `lib/tokenized-strategy/src/TokenizedStrategy.sol:1356` to `lib/tokenized-strategy/src/TokenizedStrategy.sol:1363` and `src/BaseLSTAccumulator.sol:158` to `src/BaseLSTAccumulator.sol:162`, but a keeper can re-stake the freed WETH before users withdraw.

Likelihood: role-restricted to keeper or management, but those roles are expected to call report/tend routinely, and `stakeAsset=false` is not an effective pause for all staking paths. Recovery requires management intervention, keeper rotation, or careful ordering; emergencyAdmin alone cannot rotate keeper. Severity is MEDIUM by high exit-liquidity impact and role-limited likelihood.

### DGF-02: MEDIUM - Lido withdrawal return data shape is inconsistent with the keeper claim decoder, leaving `pendingRedemptions` and reports stuck under the natural call flow

`initiateLSTWithdrawal` increases `pendingRedemptions` before returning the child hook's return data: `src/BaseLSTAccumulator.sol:259` to `src/BaseLSTAccumulator.sol:263`. The stETH implementation requests one Lido withdrawal and returns `abi.encode(requestIds)`, where `requestIds` is a `uint256[]`: `src/Strategy.sol:91` to `src/Strategy.sol:99`.

The corresponding keeper claim path accepts `bytes` but decodes it as a single `uint256`: `src/Strategy.sol:104` to `src/Strategy.sol:109`. Passing the bytes returned by `initiateLSTWithdrawal` into `claimLSTWithdrawal` therefore does not decode the first request id; ABI-encoded dynamic arrays start with an offset word. The claim can revert or attempt the wrong request id, leaving `pendingRedemptions` uncleared.

This matters because reports are hard-blocked while `pendingRedemptions != 0`: `src/BaseLSTAccumulator.sol:146` to `src/BaseLSTAccumulator.sol:148`. The normal claim path only decrements by the amount of ETH received at `src/BaseLSTAccumulator.sol:269` to `src/BaseLSTAccumulator.sol:272`. Recovery paths exist, but they are privileged and operationally heavier: management can force-decrement with `clearPendingRedemptions` at `src/BaseLSTAccumulator.sol:279` to `src/BaseLSTAccumulator.sol:280`, and emergencyAuthorized can batch-claim with Lido hints and optionally zero all redemptions at `src/Strategy.sol:116` to `src/Strategy.sol:125`.

Impact: after a queued withdrawal, a keeper following the returned `returnData` cannot cleanly clear the report lock. Reports, health checks, fee accounting, and profit/loss recognition remain unavailable until management/emergency intervention. Funds are not stolen, and emergency paths can recover if correct request ids/hints are known. Severity is MEDIUM by temporary accounting/report DoS with privileged recovery.

### DGF-03: LOW - Strategy4626 inherits hard report/deposit/exit DoS from the configured external ERC4626 vault

The Strategy4626 constructor only checks that `vault.asset() == wstETH`: `src/Strategy4626.sol:20` to `src/Strategy4626.sol:23`. There is no allowlist or behavioral check in the public factory deployment path at `src/Strategy4626Factory.sol:43` to `src/Strategy4626Factory.sol:68`.

Once deployed, core strategy liveness depends on live vault behavior:
- Deposits and report staking capacity call `vault.maxDeposit(address(this))`: `src/Strategy4626.sol:55` to `src/Strategy4626.sol:63`.
- Accounting calls `vault.convertToAssets(vault.balanceOf(address(this)))`: `src/Strategy4626.sol:69` to `src/Strategy4626.sol:75`, then feeds base `estimatedTotalAssets` at `src/BaseLSTAccumulator.sol:177` to `src/BaseLSTAccumulator.sol:178` and report at `src/BaseLSTAccumulator.sol:146` to `src/BaseLSTAccumulator.sol:155`.
- Staking deposits all loose wstETH into the vault at `src/Strategy4626.sol:29` to `src/Strategy4626.sol:42`.
- Exits depend on `previewWithdraw`, `maxRedeem`, and `redeem` in `_freeStETH`: `src/Strategy4626.sol:77` to `src/Strategy4626.sol:96`, with queue initiation requiring enough stETH after freeing at `src/Strategy4626.sol:49` to `src/Strategy4626.sol:52`.

A paused, malicious, or otherwise nonstandard vault can make deposits revert, make `report` revert through accounting, or cap/deny exits with `maxRedeem == 0`/reverting `redeem`. This is not a public grief against a trusted vault, but it is a real integration lockup mode for arbitrary Strategy4626 deployments. Severity is LOW as an external-dependency/selection risk; it becomes higher only if governance treats arbitrary factory deployments as endorsed without vetting vault liveness semantics.

### DGF-04: LOW - Unbounded `reportBuffer` lets management brick accounting views and reports until corrected

`setReportBuffer` has no upper bound at `src/BaseLSTAccumulator.sol:198` to `src/BaseLSTAccumulator.sol:200`, while `estimatedTotalAssets` computes `MAX_BPS - reportBuffer` at `src/BaseLSTAccumulator.sol:177` to `src/BaseLSTAccumulator.sol:178`. Setting `reportBuffer > MAX_BPS` underflows in Solidity 0.8 and reverts.

This can block `estimatedTotalAssets`, local deposit-limit calculations at `src/BaseLSTAccumulator.sol:96` to `src/BaseLSTAccumulator.sol:103`, Strategy4626 accounting through `valueOfLST`, and keeper reports at `src/BaseLSTAccumulator.sol:146` to `src/BaseLSTAccumulator.sol:155`. Only management can set and correct the value, so this is a trusted-role configuration DoS rather than an untrusted attack. Severity is LOW.

### DGF-05: INFO - Factory zero-address role settings can brick future deployments, but only through deployer/management misconfiguration

The factory constructor stores role addresses without validation at `src/Strategy4626Factory.sol:24` to `src/Strategy4626Factory.sol:35`, and `setAddresses` can set `management`, `performanceFeeRecipient`, `keeper`, or `emergencyAdmin` to zero at `src/Strategy4626Factory.sol:72` to `src/Strategy4626Factory.sol:83`. If factory `management` is set to zero, future `setAddresses` calls are impossible because they require `msg.sender == management`: `src/Strategy4626Factory.sol:78` to `src/Strategy4626Factory.sol:79`.

Future deployments also use these stored values during `newStrategy4626`: `src/Strategy4626Factory.sol:52` to `src/Strategy4626Factory.sol:64`. The inherited strategy setter rejects zero pending management at `lib/tokenized-strategy/src/TokenizedStrategy.sol:1502` to `lib/tokenized-strategy/src/TokenizedStrategy.sol:1504` and zero performance fee recipient at `lib/tokenized-strategy/src/TokenizedStrategy.sol:1572` to `lib/tokenized-strategy/src/TokenizedStrategy.sol:1577`, so a zero factory value can make public deployment revert. Zero keeper/emergencyAdmin are allowed by `lib/tokenized-strategy/src/TokenizedStrategy.sol:1528` to `lib/tokenized-strategy/src/TokenizedStrategy.sol:1545`, leaving management as the only report/emergency actor per `lib/tokenized-strategy/src/TokenizedStrategy.sol:319` to `lib/tokenized-strategy/src/TokenizedStrategy.sol:338`.

This is deployment/management hygiene, not an untrusted exploit. Severity is INFO unless a deployment process exposes the factory with stale/zero role values before intended configuration.

## Non-Findings / Rejected Ideas

- Public factory front-run is mostly benign when factory roles are already correct. Anyone can call `newStrategy4626` first for a vault, but the factory deploys the strategy itself and immediately applies factory-controlled roles at `src/Strategy4626Factory.sol:52` to `src/Strategy4626Factory.sol:64`; the caller does not receive management. The legitimate transaction may revert on `AlreadyDeployed` at `src/Strategy4626Factory.sol:43` to `src/Strategy4626Factory.sol:46`, but the recorded deployment is still the factory-configured strategy. The stale/zero-role version is covered as DGF-05.

- Factory storage bloat via arbitrary vaults is economically self-limiting. The public function writes one mapping slot per vault at `src/Strategy4626Factory.sol:68`, but it also requires a full strategy deployment at `src/Strategy4626Factory.sol:52`; no factory function iterates over deployments, and `isDeployedStrategy` only checks one vault mapping entry at `src/Strategy4626Factory.sol:85` to `src/Strategy4626Factory.sol:87`.

- Reverting withdrawal receiver does not block other users. TokenizedStrategy validates nonzero receiver and transfers WETH only to the caller-selected receiver in the individual `_withdraw` path at `lib/tokenized-strategy/src/TokenizedStrategy.sol:997` to `lib/tokenized-strategy/src/TokenizedStrategy.sol:1044`. There is no shared payout loop where one bad receiver blocks all withdrawals.

- Raw ETH donation/force-send does not inflate Lido claim accounting. The strategy accepts ETH at `src/Strategy.sol:36`, but `_claimLSTWithdrawal` snapshots `preBalance` before the Lido claim and subtracts it from the post-claim balance at `src/Strategy.sol:107` to `src/Strategy.sol:109`; pre-existing donated ETH does not reduce `pendingRedemptions`. Swap/claim paths wrap the full ETH balance into WETH at `src/Strategy.sol:80` to `src/Strategy.sol:81`, `src/Strategy.sol:111` to `src/Strategy.sol:112`, and `src/Strategy.sol:120` to `src/Strategy.sol:125`. A large donation may later appear as profit once wrapped, but it is not a direct DoS.

- Curve/Lido route failure is a trusted external dependency, not a low-cost public grief found here. The staking path uses Curve only when `get_dy` quotes above 1:1 and sets `_min_to_amount = amount` at `src/Strategy.sol:57` to `src/Strategy.sol:65`; otherwise it submits to Lido at `src/Strategy.sol:66` to `src/Strategy.sol:69`. Manual stETH-to-WETH swaps are management-only and use management-supplied `_minOut` at `src/BaseLSTAccumulator.sol:241` to `src/BaseLSTAccumulator.sol:245` and `src/Strategy.sol:74` to `src/Strategy.sol:81`. Lido staking pause intentionally blocks new deposits through `src/Strategy.sol:38` to `src/Strategy.sol:42`.

- The Lido queue report lock itself is intentional. `pendingRedemptions` blocking report at `src/BaseLSTAccumulator.sol:146` to `src/BaseLSTAccumulator.sol:148` is a deliberate accounting guard while stETH sits in the withdrawal queue. The concrete concern is the return-data mismatch in DGF-02 and role availability around the privileged recovery paths, not the existence of the lock.

- Strategy4626 emergency exit requires multiple manual steps but has intended escape hatches. Inherited `emergencyWithdraw` only sees loose stETH via `balanceOfLST` at `src/BaseLSTAccumulator.sol:158` to `src/BaseLSTAccumulator.sol:162`, so vaulted wstETH may first need `manualRedeem` and `manualUnwrap` at `src/Strategy4626.sol:103` to `src/Strategy4626.sol:115`. This is an operational requirement rather than a standalone bug, unless paired with an external vault that blocks redemption as in DGF-03.

## Suggested PoCs

### PoC for DGF-01

Sketch:
1. Deploy the base strategy or Strategy4626 and deposit WETH so funds are staked.
2. As management/emergencyAdmin, create loose WETH for exits: either call `manualSwapToAsset`, or call `shutdownStrategy` then `emergencyWithdraw`.
3. Assert `availableWithdrawLimit(user) > 0` and/or `maxWithdraw(user) > 0`.
4. As keeper, call `tend()` or `report()` while shutdown is true or while `stakeAsset == false`.
5. Assert loose WETH drops, LST/vault exposure increases, and `maxWithdraw(user)` falls back toward zero.

Suggested command after adding the focused test:

```bash
forge test --match-test test_keeperCanRestakeEmergencyLiquidityAfterShutdown -vv --skip 'src/test/*PoC*.t.sol'
```

Variant command for the active-state pause case:

```bash
forge test --match-test test_reportAndTendIgnoreStakeAssetFalse -vv --skip 'src/test/*PoC*.t.sol'
```

### PoC for DGF-02

Sketch:
1. Use the existing withdrawal-queue mock or a fork where the request can be finalized.
2. As management, call `initiateLSTWithdrawal(amount)` and store the returned `bytes`.
3. Finalize/prepare the withdrawal request.
4. As keeper, call `claimLSTWithdrawal(returnedBytes)`.
5. Show the call decodes the dynamic-array ABI payload as a scalar request id and either reverts or leaves `pendingRedemptions` nonzero; then show `report()` still reverts with `"Pending redemptions"`.
6. Show the recovery path works only by passing correctly encoded scalar request id, `manualClaimWithdrawals` with hints, or `clearPendingRedemptions`.

Suggested command after adding the focused test:

```bash
forge test --match-test test_claimLSTWithdrawalRejectsInitiateReturnData -vv --skip 'src/test/*PoC*.t.sol'
```
