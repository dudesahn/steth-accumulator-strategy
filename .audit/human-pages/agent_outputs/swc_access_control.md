# SWC and Access-Control Lane

## Coverage

Scope read for this lane:

- Human Pages context: `.audit/human-pages/contract_brief.md`, `.audit/human-pages/entry_points.md`, `.audit/human-pages/invariants.md`, `.audit/human-pages/static_analysis.md`.
- Local production/deployment source: `src/BaseLSTAccumulator.sol`, `src/Strategy.sol`, `src/Strategy4626.sol`, `src/Strategy4626Factory.sol`, `src/periphery/StrategyAprOracle.sol`, `src/interfaces/*`, `script/Deploy*.s.sol`.
- Inherited security-critical Yearn surfaces: `lib/tokenized-strategy/src/BaseStrategy.sol`, `lib/tokenized-strategy/src/TokenizedStrategy.sol`, `lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol`.

SWC pass:

- SWC-100/default visibility: no production functions or state variables rely on default visibility. Functions and variables are explicit.
- SWC-101/overflow-underflow: Solidity 0.8.23 checks arithmetic. Relevant unchecked blocks are in inherited TokenizedStrategy accounting and are bounded by surrounding comparisons. One local management setter can still cause checked underflow/reverts; see trusted-role risk below.
- SWC-102/SWC-103/compiler: local production contracts use `^0.8.23` or `^0.8.18`, while `foundry.toml:5` pins `solc = "0.8.23"`. Floating pragmas are not a production finding under the pinned build.
- SWC-104/unchecked calls: production token movements use `SafeERC20`/`forceApprove` or high-level interface calls that revert on failure. No low-level unchecked `call` return in production strategy source.
- SWC-105/unprotected ether withdrawal: no public ETH withdrawal path. `receive()` accepts ETH at `src/Strategy.sol:36`; ETH is wrapped into WETH during swap/claim paths at `src/Strategy.sol:80-81`, `src/Strategy.sol:111-112`, and `src/Strategy.sol:125`.
- SWC-106/selfdestruct: no `selfdestruct`.
- SWC-107/reentrancy baseline: inherited user entry points are `nonReentrant` for deposit/mint/withdraw/redeem/report/tend/emergencyWithdraw at `lib/tokenized-strategy/src/TokenizedStrategy.sol:487-635`, `1081-1085`, `1314`, and `1356-1358`. Local role functions are not `nonReentrant`, but their external callees are hardcoded WETH/Lido/Curve or the configured ERC4626 vault and are role-gated.
- SWC-108/state variable visibility: explicit visibility on local production state.
- SWC-110/assert: no local production `assert`.
- SWC-111/deprecated functions: no `suicide`, `throw`, `callcode`, or `now`.
- SWC-112/delegatecall: inherited fallback delegates all unknown calls to a hardcoded Yearn TokenizedStrategy implementation at `lib/tokenized-strategy/src/BaseStrategy.sol:100-101` and `485-511`. The callee is not user-controlled; deployment must remain on chains where that implementation address is intended.
- SWC-113/failed-call DoS: public withdrawals are limited to loose WETH at `src/BaseLSTAccumulator.sol:133-143`; Lido queue batch claim is emergency-role-only at `src/Strategy.sol:116-126`.
- SWC-114/transaction-order dependence: public factory deployment can be front-run, but the caller receives no role in the strategy and `deployments[vault]` points to a factory-configured strategy. No concrete asset theft path found.
- SWC-115/tx.origin: no `tx.origin`.
- SWC-116/block values: `block.basefee` only gates `tendTrigger` at `src/BaseLSTAccumulator.sol:169-170`; inherited `block.timestamp` is used for profit unlock accounting, not authorization or randomness.
- SWC-118/constructor naming, SWC-119/shadowing, SWC-120/randomness, SWC-124/arbitrary storage writes, SWC-125/inheritance order, SWC-127/function pointer jumps, SWC-128/block gas loops, SWC-129/typographical assignment, SWC-130/RTL override, SWC-134/hardcoded gas, SWC-135/no-effect code, SWC-136/private data: no concrete production finding in the reviewed source.
- SWC-131/unused variables: `BaseLSTAccumulator.WAD` at `src/BaseLSTAccumulator.sol:24` is unused; informational only.
- SWC-132/unexpected ETH balance: direct ETH donations are possible via `receive()`, but later wrap paths convert full ETH balance to WETH. This is donation/accounting noise, not a drain path.

State-machine coverage:

| State | Entry transitions checked | Exit transitions checked | Notes |
|---|---|---|---|
| Active | constructor/init via `BaseStrategy` delegates TokenizedStrategy initialization at `lib/tokenized-strategy/src/BaseStrategy.sol:138-150`; deposits require non-shutdown maxDeposit at `lib/tokenized-strategy/src/TokenizedStrategy.sol:499-510` | deposit/report/tend can stake WETH; shutdown by management/emergency | role gates resolve through `requireManagement`, `requireKeeperOrManagement`, and `requireEmergencyAuthorized` at `lib/tokenized-strategy/src/TokenizedStrategy.sol:306-338` |
| StakedStETH | `_stake` converts WETH to stETH through Curve or Lido at `src/Strategy.sol:51-69` | management swap, queue initiation, shutdown emergency withdraw | public withdraws do not unstake because `_freeFunds` intentionally no-ops at `src/BaseLSTAccumulator.sol:115-124` |
| PendingQueue | management increments `pendingRedemptions` before Lido request at `src/BaseLSTAccumulator.sol:259-263`; Lido queue receives approved stETH at `src/Strategy.sol:91-99` | keeper claim decrements by received ETH at `src/BaseLSTAccumulator.sol:269-272`; management/emergency can manually clear/claim | report correctly reverts while nonzero at `src/BaseLSTAccumulator.sol:146-148` |
| VaultedWstETH | Strategy4626 wraps stETH and deposits wstETH at `src/Strategy4626.sol:29-42` | redeem/unwrap in `_freeStETH` at `src/Strategy4626.sol:77-96`; emergency manual redeem/unwrap at `src/Strategy4626.sol:103-115` | vault must report `asset() == wstETH` at `src/Strategy4626.sol:20-23` |
| IdleWETH | deposits with `stakeAsset=false`, claims, swaps, or emergency withdraw leave WETH | report/tend/manualStake can stake | see MEDIUM candidate: shutdown does not suppress report/tend restaking |
| Shutdown | inherited one-way switch at `lib/tokenized-strategy/src/TokenizedStrategy.sol:1337-1340`; deposits/mints blocked through `_maxDeposit/_maxMint` at `lib/tokenized-strategy/src/TokenizedStrategy.sol:869-887` | withdraw/redeem remain liquid-only; emergency withdraw requires shutdown at `lib/tokenized-strategy/src/TokenizedStrategy.sol:1356-1363` | local report/tend can move IdleWETH back to staked/vaulted exposure |
| Factory deployment | public `newStrategy4626` checks one-per-vault at `src/Strategy4626Factory.sol:43-46`; configures roles at `src/Strategy4626Factory.sol:52-64`; writes mapping at `src/Strategy4626Factory.sol:68` | current factory management can rotate role config at `src/Strategy4626Factory.sol:72-83` | Slither reentrancy signal is not confirmed; zero-address misconfig remains a trusted-role risk |

## Candidates

### MEDIUM - Shutdown report/tend can restake WETH freed for emergency exits

Impact: Medium. After shutdown, emergency unwinding is expected to move illiquid stETH exposure back to liquid WETH so users can withdraw. This implementation can move that WETH back into stETH or the ERC4626 vault through keeper-accessible maintenance calls, delaying withdrawals and undermining the Shutdown -> IdleWETH terminal recovery path.

Likelihood: Medium-low. The transition requires keeper or management after shutdown, not an arbitrary attacker. However keepers are commonly automated, and TokenizedStrategy explicitly allows `report()` and `tend()` after shutdown for maintenance.

Evidence:

- Shutdown is one-way and blocks new deposits, but inherited comments state `tend` and `report` are still allowed after shutdown at `lib/tokenized-strategy/src/TokenizedStrategy.sol:1325-1335`; `shutdownStrategy()` only sets `shutdown = true` at `lib/tokenized-strategy/src/TokenizedStrategy.sol:1337-1340`.
- `emergencyWithdraw()` requires shutdown and calls the strategy's shutdown withdrawal hook at `lib/tokenized-strategy/src/TokenizedStrategy.sol:1356-1363`.
- The local emergency hook swaps stETH to WETH at `src/BaseLSTAccumulator.sol:158-163`, creating the intended Shutdown/IdleWETH state.
- The local report path then unconditionally stakes loose WETH at `src/BaseLSTAccumulator.sol:146-155`. Its deposit-limit call uses `availableDepositLimit(address(this))`; `address(this)` is whitelisted in the constructor at `src/BaseLSTAccumulator.sol:64`, and the local limit check does not query `TokenizedStrategy.isShutdown()` at `src/BaseLSTAccumulator.sol:126-130`.
- The local tend path also stakes all supplied idle WETH at `src/BaseLSTAccumulator.sol:165-166`.
- `_stake` converts WETH into stETH through Curve/Lido at `src/Strategy.sol:51-69`, and Strategy4626 then wraps/deposits into the external vault at `src/Strategy4626.sol:29-42`.
- User withdrawals remain capped to loose WETH only at `src/BaseLSTAccumulator.sol:133-143`, so restaking reduces immediately withdrawable liquidity.

State transition:

`Shutdown + IdleWETH` after `emergencyWithdraw` should remain liquid for exits. Instead, `keeper.report()` or `keeper.tend()` can transition it to `Shutdown + StakedStETH` or `Shutdown + VaultedWstETH`.

Suggested fix direction:

- In `_harvestAndReport`, skip `_stake(...)` when `TokenizedStrategy.isShutdown()` is true.
- In `_tend`, no-op when shutdown.
- Optionally make local `availableDepositLimit` return zero when shutdown, including for `address(this)`, so internal self-deploy limits cannot bypass shutdown intent.

### LOW - Factory role rotation accepts zero addresses and can brick future deployments

Impact: Low. Current factory `management` can set factory `management` to zero, after which `setAddresses` is permanently inaccessible and future `newStrategy4626` calls revert when the factory tries `setPendingManagement(address(0))`. Setting `performanceFeeRecipient` to zero similarly makes future deployments revert at the strategy setter. Setting keeper/emergency admin to zero creates strategies that lack those configured roles until pending management accepts and fixes them.

Likelihood: Low. This requires the trusted factory management role or deployment-time misconfiguration. Existing deployed strategies are not directly drained.

Evidence:

- The factory constructor copies all role/asset inputs without zero checks at `src/Strategy4626Factory.sol:24-35`.
- `setAddresses` gates only on `msg.sender == management`, then writes all four addresses without validation at `src/Strategy4626Factory.sol:72-83`.
- `newStrategy4626` consumes these stored values during deployment/configuration at `src/Strategy4626Factory.sol:52-64`.
- The inherited strategy setter rejects zero pending management at `lib/tokenized-strategy/src/TokenizedStrategy.sol:1502-1504` and zero performance fee recipient at `lib/tokenized-strategy/src/TokenizedStrategy.sol:1572-1577`, so zero values can turn future factory deployments into guaranteed reverts.
- The inherited keeper and emergency admin setters do not reject zero at `lib/tokenized-strategy/src/TokenizedStrategy.sol:1528-1545`.

Suggested fix direction:

- Reject zero `_management`, `_performanceFeeRecipient`, `_keeper`, `_emergencyAdmin`, and `_asset` in the factory constructor.
- Reject zero `_management` and `_performanceFeeRecipient` in `setAddresses`; decide explicitly whether zero keeper/emergency admin is allowed and document it if so.

### LOW - `reportBuffer` can be set above `MAX_BPS` and make reports/deposit-limit views revert

Impact: Low. Management can set `reportBuffer > 10_000`, causing checked underflow in `estimatedTotalAssets()` and breaking reports and deposit-limit reads until management corrects the value.

Likelihood: Low. Requires trusted management misconfiguration and is reversible by management.

Evidence:

- `setReportBuffer` writes the value without a max bound at `src/BaseLSTAccumulator.sol:198-200`.
- `estimatedTotalAssets` computes `MAX_BPS - reportBuffer` at `src/BaseLSTAccumulator.sol:177-178`; with Solidity 0.8 checked arithmetic, values above `MAX_BPS` revert.
- `_depositLimit` calls `estimatedTotalAssets()` at `src/BaseLSTAccumulator.sol:96-102`, and `_harvestAndReport` returns it during report at `src/BaseLSTAccumulator.sol:146-155`.

Suggested fix direction:

- Add `require(_reportBuffer <= MAX_BPS, "!reportBuffer")` or equivalent to the setter.

### INFO - Direct Strategy4626 deployment script does not hand off management despite logging that it should

Impact: Informational deployment footgun. The direct `Deploy4626` script defines an intended `management` and logs that management must call `acceptManagement()`, but it never calls `setPendingManagement(management)` or role setters. A direct deployment with this script leaves the broadcaster as actual management from the inherited constructor initialization.

Likelihood: Deployment-process dependent. The factory deployment path does configure pending management.

Evidence:

- `script/Deploy4626.s.sol:12-19` defines `management` and deploys `new Strategy4626(...)`.
- Unlike `script/Deploy.s.sol:23-29`, it does not call `setPendingManagement`, `setKeeper`, `setEmergencyAdmin`, or `setPerformanceFeeRecipient`.
- It still logs a handoff note at `script/Deploy4626.s.sol:26-28`.

Suggested fix direction:

- Mirror the handoff calls from `Deploy.s.sol` or remove the misleading management variable/log from the direct script.

## Non-Findings / Rejected Ideas

- Slither: `Strategy4626Factory.newStrategy4626` writes `deployments[_vault]` after external calls. I do not confirm this as exploitable reentrancy. `ERC20(_vault).symbol()` at `src/Strategy4626Factory.sol:48` and `IERC4626(_vault).asset()` inside `Strategy4626` at `src/Strategy4626.sol:20-21` are `view` high-level calls compiled as static calls, so a malicious vault cannot statefully reenter factory deployment from those calls. The later setter calls at `src/Strategy4626Factory.sol:54-64` target the freshly deployed strategy and route to inherited setters with no user-controlled external callback. Hardening by writing the mapping earlier is reasonable, but the current trace does not produce duplicate deployments or role takeover.
- Slither: missing zero check in `Strategy.setReferral`. Rejected. `referral` is only passed to Lido `submit` at `src/Strategy.sol:67-68`, and zero is the default/valid no-referral value. The setter is management-only at `src/Strategy.sol:128-130`.
- Public factory deployment is not an access-control bypass. Anyone can pay gas to call `newStrategy4626`, but the strategy is initialized/configured with factory-held roles and pending factory management at `src/Strategy4626Factory.sol:52-64`; the caller receives no local authority.
- Public deposits/withdrawals are expected ERC4626 behavior, not unprotected asset movement. Deposits/mints are blocked by shutdown and `maxDeposit/maxMint` at `lib/tokenized-strategy/src/TokenizedStrategy.sol:499-535`; withdrawals/redeems require owner allowance and are capped by loose WETH at `lib/tokenized-strategy/src/TokenizedStrategy.sol:565-635` and `src/BaseLSTAccumulator.sol:133-143`.
- The hardcoded Yearn delegatecall fallback is not SWC-112 in the usual untrusted-callee sense. The implementation address is constant at `lib/tokenized-strategy/src/BaseStrategy.sol:100-101`, and fallback delegates only there at `lib/tokenized-strategy/src/BaseStrategy.sol:485-511`.
- `manualClaimWithdrawals(..., zeroRedemptions=true)` can zero pending redemptions at `src/Strategy.sol:116-126`, but it is `onlyEmergencyAuthorized` and documented/expected as an emergency unstick path. Misuse can force accounting losses, but this is an explicit trusted-role risk rather than an external bypass.
- `clearPendingRedemptions` can also force later loss recognition at `src/BaseLSTAccumulator.sol:279-281`, but it is management-only and documented as an emergency recovery control at `src/BaseLSTAccumulator.sol:275-278`.
- `block.basefee` in `_tendTrigger` at `src/BaseLSTAccumulator.sol:169-170` can affect keeper liveness, but not authorization or asset accounting.
- `receive()` at `src/Strategy.sol:36` allows unsolicited ETH. Later claim/swap paths wrap the full ETH balance into WETH, so unsolicited ETH is a donation/accounting nuisance, not an attacker withdrawal path.
- The Lido queue claim ABI is operator-sensitive: `_initiateLSTWithdrawal` returns `abi.encode(requestIds)` at `src/Strategy.sol:97-99`, while `_claimLSTWithdrawal` expects bytes that decode to a scalar request id at `src/Strategy.sol:104-108`. This can confuse off-chain operators if they reuse return bytes directly, but the keeper can pass `abi.encode(requestIds[0])`, and emergency batch claim exists. I did not classify this as an access-control or state-machine exploit.

Expected trusted-role powers:

- Management can open/close deposits, whitelist receivers, adjust deposit limit, stake toggle, tend thresholds, report buffer, manual stake/swap, initiate/clear queue redemptions, and set Lido referral at `src/BaseLSTAccumulator.sol:198-281` and `src/Strategy.sol:128-130`.
- Keeper can report/tend and claim queued withdrawals at `lib/tokenized-strategy/src/TokenizedStrategy.sol:1081-1085`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1314`, and `src/BaseLSTAccumulator.sol:269-272`.
- Emergency admin/management can shutdown, emergencyWithdraw, manual batch claim, and Strategy4626 manual redeem/unwrap at `lib/tokenized-strategy/src/TokenizedStrategy.sol:1337-1363`, `src/Strategy.sol:116-126`, and `src/Strategy4626.sol:103-115`.

## Suggested PoCs

### PoC sketch for MEDIUM: shutdown maintenance restakes freed WETH

Create `src/test/ShutdownRestakePoC.t.sol` or add an equivalent test to the existing shutdown suite:

```solidity
function test_shutdownTendRestakesFreedWeth() public {
    // 1. Deposit WETH into the strategy and let the strategy stake it to stETH.
    // 2. As management/emergency admin, call shutdownStrategy().
    // 3. As management/emergency admin, call emergencyWithdraw(type(uint256).max).
    // 4. Assert WETH balance of the strategy is now nonzero.
    // 5. As keeper, call tend() after shutdown.
    // 6. Assert WETH balance fell and stETH or wstETH/vault exposure rose.
    // 7. Assert availableWithdrawLimit(user) fell, proving the shutdown liquid-exit state was undone.
}
```

Suggested command:

```bash
ETH_RPC_URL=<mainnet_rpc> forge test --match-path src/test/ShutdownRestakePoC.t.sol --match-test test_shutdownTendRestakesFreedWeth -vv --fork-url "$ETH_RPC_URL" --skip 'src/test/*PoC*.t.sol'
```

### Lower-severity regression tests

Factory zero-address hardening:

```bash
forge test --match-test 'test_factoryRejectsZeroAddressConfig|test_factorySetManagementZeroWouldBrickDeployments' -vv --skip 'src/test/*PoC*.t.sol'
```

Report-buffer bound:

```bash
forge test --match-test test_setReportBufferRejectsAboveMaxBps -vv --skip 'src/test/*PoC*.t.sol'
```
